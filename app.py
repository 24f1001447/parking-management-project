from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

from models import db, User, ParkingLot, ParkingSpot, Reservation
from forms import LoginForm, RegisterForm, LotForm

app = Flask(__name__)
app.config.from_object('config.Config')
db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user = User(username=form.username.data, password=hashed_password, role='user')
        db.session.add(user)
        db.session.commit()
        flash('Registered successfully. Please login.')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('admin_dashboard' if user.role == 'admin' else 'user_dashboard'))
        flash('Invalid username or password.')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))
    lots = ParkingLot.query.all()
    return render_template('admin_dashboard.html', lots=lots)


@app.route('/user')
@login_required
def user_dashboard():
    if current_user.role != 'user':
        return redirect(url_for('admin_dashboard'))

    lots = ParkingLot.query.all()

    active_reservation = Reservation.query.filter_by(
        user_id=current_user.id,
        end_time=None
    ).first()

    return render_template(
        'user_dashboard.html',
        lots=lots,
        reservation=active_reservation  
    )

@app.route('/create-lot', methods=['GET', 'POST'])
@login_required
def create_lot():
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    form = LotForm()
    if form.validate_on_submit():
        lot = ParkingLot(name=form.name.data, address=form.address.data, pin=form.pin.data,
                         price=form.price.data, max_spots=form.max_spots.data)
        db.session.add(lot)
        db.session.commit()

        for i in range(lot.max_spots):
            spot = ParkingSpot(lot_id=lot.id, status='A')
            db.session.add(spot)
        db.session.commit()

        flash('Parking Lot created successfully!')
        return redirect(url_for('admin_dashboard'))
    return render_template('create_lot.html', form=form)


@app.route('/admin/lot/edit/<int:lot_id>', methods=['GET', 'POST'])
@login_required
def edit_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    form = LotForm(obj=lot)
    if form.validate_on_submit():
        lot.name = form.name.data
        lot.address = form.address.data
        lot.pin = form.pin.data
        lot.price = form.price.data
        lot.max_spots = form.max_spots.data
        db.session.commit()
        flash('Parking lot updated successfully.', 'info')
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_lot.html', form=form, lot=lot)


@app.route('/admin/lot/delete/<int:lot_id>', methods=['GET', 'POST'])
@login_required
def delete_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    db.session.delete(lot)
    db.session.commit()
    flash('Parking lot deleted successfully.', 'danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/lot/<int:lot_id>/spots')
@login_required
def view_spots(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()

    reservations_by_spot = {}
    for spot in spots:
        reservations = Reservation.query.filter_by(spot_id=spot.id).order_by(Reservation.start_time.desc()).all()
        reservations_by_spot[spot.id] = reservations

    active_reservations = {}
    for spot_id, reservations in reservations_by_spot.items():
        active = next((r for r in reservations if not r.end_time), None)
        active_reservations[spot_id] = active

    return render_template(
        'view_spots.html',
        lot=lot,
        spots=spots,
        reservations_by_spot=reservations_by_spot,
        active_reservations=active_reservations 
    )


@app.route('/admin/lot/<int:lot_id>/spot/delete/<int:spot_id>', methods=['POST'])
@login_required
def delete_spot(lot_id, spot_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))

    spot = ParkingSpot.query.get_or_404(spot_id)
    if spot.status == 'A':
        db.session.delete(spot)
        db.session.commit()
        flash('Spot deleted successfully.', 'success')
    else:
        flash('Cannot delete an occupied spot.', 'danger')

    return redirect(url_for('view_spots', lot_id=lot_id))


@app.route('/book/<int:lot_id>', methods=['POST'])
@login_required
def book_spot(lot_id):
    if current_user.role != 'user':
        return redirect(url_for('admin_dashboard'))

    spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()

    if not spot:
        flash("No available spots in this lot.", "danger")
        return redirect(url_for('user_dashboard'))

    spot.status = 'O' 

    reservation = Reservation(
        user_id=current_user.id,
        spot_id=spot.id,
        start_time=datetime.now(),
        end_time=None,  
        cost=spot.lot.price  
    )

    db.session.add(reservation)
    db.session.commit()

    flash(f"Spot {spot.id} booked successfully!", "success")
    return redirect(url_for('user_dashboard'))

@app.route('/book-form', methods=['GET', 'POST'])
@login_required
def show_booking_form():
    lots = ParkingLot.query.all()
    if request.method == 'POST':
        lot_id = request.form.get('lot_id')

        spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()
        if not spot:
            flash("No spots available.", "danger")
            return redirect(url_for('user_dashboard'))

        spot.status = 'O'
        reservation = Reservation(
            user_id=current_user.id,
            spot_id=spot.id,
            start_time=datetime.now(),
            end_time=None,
            cost=spot.lot.price,
        )
        db.session.add(reservation)
        db.session.commit()
        flash("Spot booked successfully!", "success")
        return redirect(url_for('user_dashboard'))

    return render_template('book_form.html', lots=lots)

@app.route('/release/<int:reservation_id>', methods=['POST'])
@login_required
def release_spot(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)

    if reservation.user_id != current_user.id:
        flash("Unauthorized", "danger")
        return redirect(url_for('user_dashboard'))

    reservation.end_time = datetime.now()

    # Calculate duration
    duration = reservation.end_time - reservation.start_time
    hours = round(duration.total_seconds() / 3600, 2)

    # Get price per hour
    rate = reservation.spot.lot.price
    cost = round(hours * rate, 2)
    
    if cost < rate:
        cost = rate

    reservation.cost = cost
    reservation.spot.status = 'A'
    db.session.commit()

    return render_template('release_summary.html', reservation=reservation, hours=hours, cost=cost)

@app.route('/admin/reservations')
@login_required
def all_reservations():
    if current_user.role != 'admin':
        return redirect(url_for('home'))

    reservations = Reservation.query.order_by(Reservation.start_time.desc()).all()

    return render_template('admin_reservations.html', reservations=reservations)

@app.route('/history')
@login_required
def parking_history():
    if current_user.role != 'user':
        return redirect(url_for('home'))

    reservations = Reservation.query.filter_by(user_id=current_user.id).order_by(Reservation.start_time.desc()).all()
    return render_template('history.html', reservations=reservations)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

       
        existing_admin = User.query.filter_by(username='admin1').first()

        if not existing_admin:
            hashed_pw = generate_password_hash('admin123')
            admin_user = User(username='admin1', password=hashed_pw, role='admin')
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created.")
        else:
            if existing_admin.role != 'admin':
                existing_admin.role = 'admin'
                db.session.commit()
                print("Admin user role updated to 'admin'.")
            else:
                print("Admin user already exists with correct role.")


    app.run(debug=True)

