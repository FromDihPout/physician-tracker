from flask import Flask, flash, render_template, request, url_for, redirect, session, logging
from flask_mysqldb import MySQL
from wtforms import Form, IntegerField, StringField, PasswordField, SelectField, SelectMultipleField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

# configure MySQL database
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'phystrack'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# initialize MySQL database
mysql = MySQL(app)



# webpage routing
@app.route('/', methods=['GET', 'POST'])
def index():
	if request.method =='POST':
		# get data in form fields
		username = request.form['username']
		password_candidate = request.form['password']
		
		cur = mysql.connection.cursor()
		
		# find user from database by username
		result = cur.execute("SELECT * FROM users WHERE username = %s", [username])
		
		# username not in database
		if result == 0:
			cur.close()
			error = 'Username not found'
			return render_template('index.html', error = error)
			
		else:
			data = cur.fetchone()
			password = data['password']
			
			# compare passwords
			if sha256_crypt.verify(password_candidate, password):
				# passwords match
				session['logged_in'] = True
				session['username'] = username
				return redirect(url_for('dashboard'))
			# authentication failed
			else:
				error = 'Invalid login'
				return render_template('index.html', error = error)
			cur.close()	
	return render_template('index.html')
	
	
@app.route('/register', methods = ['GET', 'POST'])
def register():
	form = RegistrationForm(request.form)
	if request.method == 'POST' and form.validate():
		username = form.username.data
		
		# check if username already exists
		cur = mysql.connection.cursor()
		result = cur.execute("SELECT * FROM users WHERE username = %s", [username]);
		if result > 0:
			cur.close()
			error = 'Username already exists'
			return render_template('register.html', form = form, error = error)
		else:
			firstname = form.firstname.data
			lastname = form.lastname.data
			email = form.email.data
			password = sha256_crypt.encrypt(str(form.password.data))
			
			# add registration information to users table
			cur.execute("INSERT users(firstname, lastname, email, username, password) VALUES(%s, %s, %s, %s, %s)", (firstname, lastname, email, username, password))
			mysql.connection.commit()
			cur.close()
			
			flash('User registered', 'success')
			return redirect(url_for('index'))
			
	return render_template('register.html', form = form)

	
# check if user logged in
def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized access. Please Login', 'danger')
			return redirect(url_for('index'))
	return wrap
	
	
@app.route('/logout')	
@is_logged_in
def logout():
	session.clear()
	return redirect(url_for('index'))
	
	
@app.route('/dashboard')
@is_logged_in
def dashboard():
	return render_template('dashboard.html')
	
	
@app.route('/clinics')
@is_logged_in
def clinics():
	cur = mysql.connection.cursor()
	result = cur.execute("SELECT * FROM clinics ORDER BY name")
	clinics = cur.fetchall()
	cur.close()
	
	if result > 0:
		return render_template('clinics.html', clinics = clinics)
	else:
		return render_template('clinics.html', msg = 'No Clinics in Database')
	
	
@app.route('/add_clinic', methods=['GET', 'POST'])
@is_logged_in	
def add_clinic():
	form = ClinicForm(request.form)
	
	# get choices for neighbourhoods from database
	cur = mysql.connection.cursor()
	cur.execute("SELECT id, name FROM neighbourhood ORDER BY name")
	neighbourhood = cur.fetchall()
	form.neighbourhoodID.choices = [(row['id'], row['name']) for row in neighbourhood]
	
	if request.method == 'POST' and form.validate():
		name = form.name.data
		primaryContact = form.primaryContact.data
		address = form.address.data
		neighbourhoodID = form.neighbourhoodID.data
		postalCode = form.postalCode.data
		phone = form.phone.data
		fax = form.fax.data
		startingTime = form.startingTime.data
		closingTime = form.closingTime.data
		creatorUserID = cur.execute("SELECT id FROM users WHERE username = %s", [session['username']]);
		
		# add registration information to clinics table
		cur.execute("INSERT clinics(name, primaryContact, address, neighbourhoodID, postalCode, phone, fax, startingTime, closingTime, creatorUserID) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (name, primaryContact, address, neighbourhoodID, postalCode, phone, fax, startingTime, closingTime, creatorUserID))
		mysql.connection.commit()
		cur.close()
			
		flash('Clinic Added', 'success')
		return redirect(url_for('dashboard'))
		
	return render_template('add_clinic.html', form = form)
	
	
@app.route('/edit_clinic/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_clinic(id):
	cur = mysql.connection.cursor()
	result = cur.execute("SELECT * FROM clinics WHERE id = %s", [id])
	clinic = cur.fetchone()
	
	form = ClinicForm(request.form)
	
	# fill fields with pre-existing data
	form.name.data = clinic['name']
	form.primaryContact.data = clinic['primaryContact']
	form.address.data = clinic['address']
	form.neighbourhoodID.data = clinic['neighbourhoodID']
	form.postalCode.data = clinic['postalCode']
	form.phone.data = clinic['phone']
	form.fax.data = clinic['fax']
	form.startingTime.data = clinic['startingTime']
	form.closingTime.data = clinic['closingTime']
	
	# get choices for neighbourhoods from database
	cur = mysql.connection.cursor()
	cur.execute("SELECT id, name FROM neighbourhood ORDER BY name")
	neighbourhood = cur.fetchall()
	form.neighbourhoodID.choices = [(row['id'], row['name']) for row in neighbourhood]
	
	if request.method == 'POST' and form.validate():
		name = request.form['name']
		primaryContact = request.form['primaryContact']
		address = request.form['address']
		neighbourhoodID = request.form['neighbourhoodID']
		postalCode = request.form['postalCode']
		phone = request.form['phone']
		fax = request.form['fax']
		startingTime = request.form['startingTime']
		closingTime = request.form['closingTime']
		
		# add registration information to physicians table
		cur.execute("UPDATE clinics SET name=%s, primaryContact=%s, address=%s, neighbourhoodID=%s, postalCode=%s, phone=%s, fax=%s, startingTime=%s, closingTime=%s, lastUpdated=CURRENT_TIMESTAMP WHERE id=%s", (name, primaryContact, address, neighbourhoodID, postalCode, phone, fax, startingTime, closingTime, id))
		mysql.connection.commit()
		cur.close()
			
		flash('Changes Saved', 'success')
		return redirect(url_for('clinics'))
		
	return render_template('edit_clinic.html', form = form)	
	
	
@app.route('/delete_clinic/<string:id>', methods=['POST'])
@is_logged_in
def delete_clinic(id):
	cur = mysql.connection.cursor()
	
	# delete records from clinics table
	cur.execute("DELETE FROM clinics WHERE id=%s", [id])
	mysql.connection.commit()
	
	# delete records from bridge table
	cur.execute("DELETE FROM clinicphysician WHERE clinicID=%s", [id])
	mysql.connection.commit()
	cur.close()
	
	flash('Clinic Deleted', 'success')
	return redirect(url_for('clinics'))
	
	
@app.route('/physicians')
@is_logged_in
def physicians():
	cur = mysql.connection.cursor()
	result = cur.execute("SELECT * FROM physicians ORDER BY lastname")
	physicians = cur.fetchall()
	cur.close()
	
	if result > 0:
		return render_template('physicians.html', physicians = physicians)
	else:
		return render_template('physicians.html', msg = 'No Physicians in Database')

	
@app.route('/add_physician', methods=['GET', 'POST'])
@is_logged_in
def add_physician():
	form = PhysicianForm(request.form)
	
	# get choices for universities from database
	cur = mysql.connection.cursor()
	cur.execute("SELECT id, name FROM universities ORDER BY name")
	universities = cur.fetchall()
	form.graduationUniversityID.choices = [(row['id'], row['name']) for row in universities]
	
	# get choices for clinics from database
	cur.execute("SELECT id, name FROM clinics ORDER BY name")
	clinics = cur.fetchall()
	form.clinicsWorked.choices = [(row['id'], row['name']) for row in clinics]
	
	if request.method == 'POST' and form.validate():
		CPSONumber = form.CPSONumber.data
		firstname = form.firstname.data
		lastname = form.lastname.data 
		email = form.email.data
		phone = form.phone.data
		fax = form.fax.data
		graduationUniversityID = form.graduationUniversityID.data
		graduationYear = form.graduationYear.data
		numberOfPatients = form.numberOfPatients.data
		clinicsWorked = form.clinicsWorked.data
		creatorUserID = cur.execute("SELECT id FROM users WHERE username = %s", [session['username']]);
		
		# add registration information to physicians table
		cur.execute("INSERT physicians(CPSONumber, firstname, lastname, email, phone, fax, graduationUniversityID, graduationYear, numberOfPatients, creatorUserID) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (CPSONumber, firstname, lastname, email, phone, fax, graduationUniversityID, graduationYear, numberOfPatients, creatorUserID))
		mysql.connection.commit()
		
		# add physician and clinics worked in to bridge table
		cur.execute("SELECT id FROM physicians WHERE CPSONumber = %s", [CPSONumber])
		physicianID = cur.fetchone()
		for clinic in clinicsWorked:
			cur.execute("INSERT clinicphysician(clinicID, physicianID) VALUES(%s, %s)", (clinic, physicianID['id']))
			mysql.connection.commit()
		cur.close()
			
		flash('Physician Added', 'success')
		return redirect(url_for('dashboard'))
		
	return render_template('add_physician.html', form = form)


@app.route('/edit_physician/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_physician(id):
	cur = mysql.connection.cursor()
	result = cur.execute("SELECT * FROM physicians WHERE id = %s", [id])
	physician = cur.fetchone()
	
	form = PhysicianForm(request.form)
	
	# fill fields with pre-existing data
	form.CPSONumber.data = physician['CPSONumber']
	form.firstname.data = physician['firstname']
	form.lastname.data = physician['lastname']
	form.email.data = physician['email']
	form.phone.data = physician['phone']
	form.fax.data = physician['fax']
	form.graduationUniversityID.data = physician['graduationUniversityID']
	form.graduationYear.data = physician['graduationYear']
	form.numberOfPatients.data = physician['numberOfPatients']
	
	# get choices for universities from database
	cur.execute("SELECT id, name FROM universities ORDER BY name")
	universities = cur.fetchall()
	form.graduationUniversityID.choices = [(row['id'], row['name']) for row in universities]
	
	# get choices for clinics from database
	cur.execute("SELECT id, name FROM clinics ORDER BY name")
	clinics = cur.fetchall()
	form.clinicsWorked.choices = [(row['id'], row['name']) for row in clinics]
	
	if request.method == 'POST' and form.validate():
		CPSONumber = request.form['CPSONumber']
		firstname = request.form['firstname']
		lastname = request.form['lastname']
		email = request.form['email']
		phone = request.form['phone']
		fax = request.form['fax']
		graduationUniversityID = request.form['graduationUniversityID']
		graduationYear = request.form['graduationYear']
		numberOfPatients = request.form['numberOfPatients']
		clinicsWorked = form.clinicsWorked.data
		
		# add registration information to physicians table
		cur.execute("UPDATE physicians SET CPSONumber=%s, firstname=%s, lastname=%s, email=%s, phone=%s, fax=%s, graduationUniversityID=%s, graduationYear=%s, numberOfPatients=%s, lastUpdated=CURRENT_TIMESTAMP WHERE id=%s", (CPSONumber, firstname, lastname, email, phone, fax, graduationUniversityID, graduationYear, numberOfPatients, id))
		mysql.connection.commit()
		
		# remove existing records from clinicphysician table
		cur.execute("DELETE FROM clinicphysician WHERE physicianID=%s", [id])
		mysql.connection.commit()
		
		# add physician and clinics worked in to bridge table
		for clinic in clinicsWorked:
			cur.execute("INSERT clinicphysician(clinicID, physicianID) VALUES(%s, %s)", (clinic, [id]))
			mysql.connection.commit()
		cur.close()
			
		flash('Changes Saved', 'success')
		return redirect(url_for('physicians'))
		
	return render_template('edit_physician.html', form = form)
	
	
@app.route('/delete_physician/<string:id>', methods=['POST'])
@is_logged_in	
def delete_physician(id):
	cur = mysql.connection.cursor()
	
	# delete records from physicians table
	cur.execute("DELETE FROM physicians WHERE id=%s", [id])
	mysql.connection.commit()
	
	# delete records from bridge table
	cur.execute("DELETE FROM clinicphysician WHERE physicianID=%s", [id])
	mysql.connection.commit()
	cur.close()
	
	flash('Physician Deleted', 'success')
	return redirect(url_for('physicians'))
	

	
# forms
class RegistrationForm(Form):
	firstname = StringField('First name', [validators.Length(min = 1, max  = 50)])
	lastname = StringField('Last name', [validators.Length(min = 1, max  = 50)])
	email = StringField('Email', [validators.Email()])
	username = StringField('Username', [validators.Length(min = 3, max = 35)])
	password = PasswordField('Password', [
		validators.DataRequired(),
		validators.EqualTo('repeat', message = 'Passwords do not match')
	])
	repeat = PasswordField('Repeat Password')


class ClinicForm(Form):
	name = StringField('Clinic Name', [validators.Length(min = 1, max  = 50)])
	primaryContact = StringField('Primary Contact', [validators.Length(min = 1, max  = 50)])
	address = StringField('Address', [validators.Length(min = 1, max  = 50)])
	neighbourhoodID = SelectField('Neighbourhood', coerce=int)
	postalCode = StringField('Postal Code', [validators.Length(min = 6, max  = 7)])
	phone = StringField('Phone (xxx-xxx-xxxx ext. xxxx)', [validators.Length(min = 10, max = 25)])
	fax = StringField('Fax (xxx-xxx-xxxx ext. xxxx)', [validators.Length(min = 10, max = 25)])
	startingTime = StringField('Start Time (24-hour format 00:00)', [validators.Length(min = 4, max  = 5)])
	closingTime = StringField('Close Time (24-hour format 00:00)', [validators.Length(min = 4, max  = 5)])

		
class PhysicianForm(Form):
	CPSONumber = IntegerField('CPSO Number', [validators.NumberRange(min = 0, max  = 99999999999)])
	firstname = StringField('First name', [validators.Length(min = 1, max  = 50)])
	lastname = StringField('Last name', [validators.Length(min = 1, max  = 50)])
	email = StringField('Email', [validators.Email()])
	phone = StringField('Phone (xxx-xxx-xxxx ext. xxxx)', [validators.Length(min = 10, max = 25)])
	fax = StringField('Fax (xxx-xxx-xxxx ext. xxxx)', [validators.Length(min = 10, max = 25)])
	graduationUniversityID = SelectField('Graduation University', coerce=int)
	graduationYear = IntegerField('Graduation Year', [validators.NumberRange(min = 1920, max  = 2019)])
	numberOfPatients = IntegerField('Number of Patients', [validators.NumberRange(min = 1, max  = 9999)])
	clinicsWorked = SelectMultipleField('Clinics', coerce=int)

	

if __name__ == '__main__':
	app.secret_key='secretpassword789'
	app.run()