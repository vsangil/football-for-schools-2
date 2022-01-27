from flask_bootstrap import Bootstrap
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, EmailField, PasswordField, SelectField, HiddenField
from wtforms.validators import DataRequired, Email, Length
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from functools import wraps
from sqlalchemy.orm import relationship
import os

app = Flask(__name__)
# Secret key for csrf token to work on wtforms.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "hello671")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL1", "sqlite:///players.db")
Bootstrap(app)

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)


class Coach(UserMixin, db.Model):
    __tablename__ = "coaches"
    id = db.Column(db.String, primary_key=True)
    phone_number = db.Column(db.String, nullable=True)
    school = db.Column(db.String, nullable=False)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)
    admin = db.Column(db.Boolean, nullable=False)

    players = relationship("Player", back_populates="coach")


class Player(db.Model):
    __tablename__ = "players"
    id = db.Column(db.Integer, primary_key=True)

    coach_id = db.Column(db.String, db.ForeignKey("coaches.id"))
    coach = relationship("Coach", back_populates="players")

    name = db.Column(db.String(50), nullable=False)
    school = db.Column(db.String(75), nullable=False)
    born_in = db.Column(db.String(7), nullable=False)



db.create_all()
db.session.commit()


# Login form which renders on home route.
class LogIn(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField(label='Login')


# Player form which renders on coach route.
class AddPlayer(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    month = StringField('Month', validators=[DataRequired(), Length(max=2, min=2)])
    year = StringField('Year', validators=[DataRequired(), Length(max=4, min=4)])
    submit = SubmitField('Add Player')


class AddCoach(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Phone Number')
    school = StringField('School - Please make sure school name is correct. This cannot be changed',
                         validators=[DataRequired()])
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    password = PasswordField('Create a password', validators=[DataRequired(), Length(min=8)])
    admin = HiddenField(validators=[Length(min=2, max=3)])
    submit = SubmitField('Add Coach')


class ChangePassword(FlaskForm):
    current_password = PasswordField(validators=[Length(min=8)])
    new_password = PasswordField(validators=[Length(min=8)])
    confirm_password = PasswordField(validators=[Length(min=8)])
    submit = SubmitField('Change Password')


@app.errorhandler(401)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('red_card.html'), 404


@login_manager.user_loader
def load_user(user_id):
    user = Coach.query.get(user_id)
    if not user:
        return render_template('red_card.html')
    return user


# Home route
@app.route('/', methods=["GET", "POST"])
def home():

    log_in_form = LogIn()

    if log_in_form.validate_on_submit():

        email = log_in_form.email.data
        password = log_in_form.password.data

        # Log in logic. Will check dictionary if email is
        # found, if not, denied access.
        coach = Coach.query.filter_by(id=email).first()

        if not coach:
            flash("That email and password combination is not correct.")
            return redirect(url_for('home'))
        elif not check_password_hash(coach.password, password):
            flash("That email and password combination is not correct.")
            return redirect(url_for('home'))
        elif coach.admin == 1:
            print("ADMIN LOGIN")
            login_user(coach)
            return redirect(url_for('admin_view'))
        elif coach.admin == 0:
            print("COACH LOGIN")
            login_user(coach)
            return redirect(url_for('coach_view', email=email))
        else:
            return render_template('red_card.html')

    return render_template('index.html', form=log_in_form)


# Coach route - Displays coaches players.
@app.route('/coach/', methods=["GET", "POST"])
@login_required
def coach_view():

    hide_header = True
    add_player = AddPlayer()
    coach = Coach.query.get(current_user.id)
    all_players = []

    # Validates form on submission
    if add_player.validate_on_submit():
        name = add_player.name.data
        month = add_player.month.data
        year = add_player.year.data
        born_in = f"{month}/{year}"

        # Create new player and commit to database
        new_player = Player(name=name, school=coach.school, born_in=born_in)
        db.session.add(new_player)
        db.session.commit()

        # We redirect instead of render because redirect clears the route
        # so there is no double submission.
        return redirect(url_for('coach_view'))

    # Tries to read players from csv if file exists
    try:
        # Get player database
        all_players = Player.query.filter_by(school=coach.school).all()

    except FileNotFoundError:
        pass

    return render_template('coach.html', form=add_player, coach=coach, players=all_players, hide_header=hide_header)


@app.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():

    hide_header = False

    email = request.args.get('email')
    player_id = request.args.get('id')
    player_to_edit = Player.query.get(player_id)
    month = player_to_edit.born_in[0:2]
    year = player_to_edit.born_in[3:7]

    if request.method == "POST":
        name = request.form.get('name')
        month = request.form.get('month')
        year = request.form.get('year')
        born_in = f"{month}/{year}"

        player_to_edit.name = name
        player_to_edit.born_in = born_in

        db.session.commit()

        return redirect(url_for('coach_view', email=email))

    return render_template('edit.html', player=player_to_edit, month=month, year=year, email=email, hide_header=hide_header, header="Edit Player")


@app.route('/delete')
@login_required
def delete():
    email = request.args.get('email')
    player_id = request.args.get('id')
    player_to_delete = Player.query.get(player_id)
    db.session.delete(player_to_delete)
    db.session.commit()

    return redirect(url_for('coach_view', email=email))


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.admin != 1:
            logout()
            return render_template('red_card.html')
        return f(*args, **kwargs)
    return decorated_function


@app.route('/admin', methods=["GET", "POST"])
@admin_only
def admin_view():

    return render_template('admin.html', form=add_coach, hide_header=False, header='Admin Dashboard')


@app.route('/logout')
def logout():
    logout_user()

    return redirect(url_for('home'))


@app.route('/register/register-coach', methods=["GET", "POST"])
def register_admin():
    form = AddCoach(school="Admin", admin="Yes")
    del form.school
    del form.phone_number

    if request.method == "POST":
        if Coach.query.filter_by(id=form.email.data).first():

            return redirect(url_for('register_admin'))

        else:
            salted_hashed_password = generate_password_hash(
                form.password.data,
                method="pbkdf2:sha256",
                salt_length=8,
            )

            new_coach = Coach(
                id=form.email.data,
                phone_number="None",
                school="Admin",
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                password=salted_hashed_password,
                admin=True,
            )

            db.session.add(new_coach)
            db.session.commit()

            return redirect(url_for("home"))

    return render_template("register.html", form=form)


@app.route('/my-account', methods=["GET", "POST"])
def my_account():
    password = ChangePassword()

    if password.validate_on_submit():
        print(f"Current password: {current_user.password}")
        if not check_password_hash(current_user.password, password.current_password.data):
            flash("Incorrect current password.")
        elif password.new_password.data != password.confirm_password.data:
            flash("Passwords do not match.")
        elif password.current_password.data == password.new_password.data:
            flash("Password cannot be the same as previous password.")
        else:
            new_password = generate_password_hash(
                password.new_password.data,
                method="pbkdf2:sha256",
                salt_length=8,
            )

            current_user.password = new_password

            db.session.commit()

            return redirect(url_for('my_account'))

    return render_template('edit_coach.html', form=password)


@app.route('/admin/players-and-coaches/view')
def view():
    data_type = request.args.get('data_type')
    hide_header = False

    if data_type == "coaches":
        items = db.session.query(Coach).all()
        header = "Edit/View Coaches"
        players = False

    else:
        players = True
        header = "All Players"
        items = db.session.query(Player).all()

    return render_template('view.html', players=players, items=items, hide_header=hide_header, header=header)


@app.route('/admin/add_coach', methods=["GET", "POST"])
def add_coach():
    coach = AddCoach(admin="No")
    del coach.admin

    if coach.validate_on_submit():
        salted_hashed_password = generate_password_hash(
            coach.password.data,
            method="pbkdf2:sha256",
            salt_length=8,
        )

        new_coach = Coach(
            id=coach.email.data,
            phone_number=coach.phone_number.data,
            school=coach.school.data,
            first_name=coach.first_name.data,
            last_name=coach.last_name.data,
            password=salted_hashed_password,
            admin=False,
        )

        db.session.add(new_coach)
        db.session.commit()

        return redirect(url_for('admin_view', form=coach))

    return render_template('add_coach.html', form=coach, hide_header=False, header='Add Coach')

if __name__ == "__main__":
    app.run()
