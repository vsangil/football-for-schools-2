import flask
from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, EmailField, PasswordField, SelectField
from wtforms.validators import DataRequired, Email, Length

app = Flask(__name__)
# Secret key for csrf token to work on wtforms.
app.secret_key = "hello671"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///players.db'


db = SQLAlchemy(app)

logged_in = False


class Coach(db.Model):
    email = db.Column(db.String, primary_key=True)
    phone_number = db.Column(db.String, nullable=True)
    school = db.Column(db.String, nullable=False)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)
    admin = db.Column(db.Boolean, nullable=False)


db.create_all()
db.session.commit()


class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
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
    school = StringField('School - Please make sure school name is correct. This cannot be changed', validators=[DataRequired()])
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    password = PasswordField('Create a password', validators=[DataRequired(), Length(min=8)])
    admin = SelectField(choices=[('No', 'No'), ('Yes', 'Yes'), ])
    submit = SubmitField('Add Coach')


# Home route
@app.route('/', methods=["GET", "POST"])
def home():
    # Creates login form.
    global logged_in
    log_in_form = LogIn()

    if log_in_form.validate_on_submit():
        email = log_in_form.email.data
        password = log_in_form.password.data

        coach = Coach.query.filter_by(email=email).first()
        # Log in logic. Will check dictionary if email is
        # found, if not, denied access.
        try:
            if coach.email == email:
                if coach.password == password:
                    print("made it here...")
                    if coach.admin == 1:
                        logged_in = True
                        return redirect(url_for('admin_view'))
                    else:
                        logged_in = True
                        print(f"Are you logged in? : {logged_in}")
                    return flask.redirect(url_for('coach_view', email=email))
            else:
                return render_template('red_card.html')
        except KeyError:
            return render_template('red_card.html')

    return render_template('index.html', form=log_in_form)


# Coach route - Displays coaches players.
@app.route('/coach/', methods=["GET", "POST"])
def coach_view():
    global logged_in
    print(f"Coach view logged in? {logged_in}")
    if logged_in:
        add_player = AddPlayer()
        email = request.args.get('email')
        coach = Coach.query.get(email)
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
            return redirect(url_for('coach_view', email=email))

        # Tries to read players from csv if file exists
        try:
            # Get player database
            all_players = Player.query.filter_by(school=coach.school).all()

        except FileNotFoundError:
            pass

        return render_template('coach.html', form=add_player, email=email, coach=coach, players=all_players)
    else:
        return render_template('red_card.html')


@app.route('/edit', methods=['GET', 'POST'])
def edit():
    if logged_in:

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

        return render_template('edit.html', player=player_to_edit, month=month, year=year, email=email)
    else:
        return render_template('red_card.html')

@app.route('/delete')
def delete():
    if logged_in:
        email = request.args.get('email')
        player_id = request.args.get('id')
        player_to_delete = Player.query.get(player_id)
        db.session.delete(player_to_delete)
        db.session.commit()

        return redirect(url_for('coach_view', email=email))


@app.route('/admin', methods=["GET", "POST"])
def admin_view():
    if logged_in:
        add_coach = AddCoach()

        if add_coach.validate_on_submit():
            email = add_coach.email.data
            phone_number = add_coach.phone_number.data
            school = add_coach.school.data
            first_name = add_coach.first_name.data
            last_name = add_coach.last_name.data
            password = add_coach.password.data
            if add_coach.admin.data == "No":
                admin = False
            else:
                admin = True

            new_coach = Coach(
                email=email,
                phone_number=phone_number,
                school=school,
                first_name=first_name,
                last_name=last_name,
                password=password,
                admin=admin,
            )

            db.session.add(new_coach)
            db.session.commit()

            return redirect(url_for('admin_view', form=add_coach))

        return render_template('admin.html', form=add_coach)
    else:
        return render_template('red_card.html')


@app.route('/logout')
def logout():
    global logged_in
    logged_in = False

    return redirect(url_for('home'))


@app.route('/register-admin/register')
def register_admin():
    pass


if __name__ == "__main__":
    app.run(debug=True)
