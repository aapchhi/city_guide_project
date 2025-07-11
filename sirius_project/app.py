from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from sqlalchemy.sql import func
from wtforms import StringField, TextAreaField, SelectField, FloatField, IntegerField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///city_guide.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

db = SQLAlchemy(app)

# Модели
class Place(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    photos = db.relationship('PlacePhoto', backref='place', cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='place', cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='place', lazy=True)
    
    
    def get_average_rating(self):
        if not self.reviews:
            return 0.0
        return round(sum(r.rating for r in self.reviews) / len(self.reviews), 1)
    
    average_rating = property(get_average_rating)

class PlacePhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    place_id = db.Column(db.Integer, db.ForeignKey('place.id'))
    filename = db.Column(db.String(100))

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    place_id = db.Column(db.Integer, db.ForeignKey('place.id'))
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)
    author = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, server_default=db.func.now())

# Формы
class PlaceForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    address = StringField('Адрес', validators=[DataRequired()])
    description = TextAreaField('Описание')
    category = SelectField('Категория', choices=[
        ('museum', 'Музей'), ('park', 'Парк'), ('cafe', 'Кафе'),
        ('restaurant', 'Ресторан'), ('landmark', 'Достопримечательность')
    ], validators=[DataRequired()])
    latitude = FloatField('Широта', validators=[DataRequired()])
    longitude = FloatField('Долгота', validators=[DataRequired()])

class ReviewForm(FlaskForm):
    rating = IntegerField('Оценка', validators=[DataRequired()])
    comment = TextAreaField('Комментарий')
    author = StringField('Ваше имя')

# Создание БД
with app.app_context():
    db.create_all()

# Маршруты
@app.route('/')
def index():
    places = Place.query.all()
    return render_template('index.html', places=places)

@app.route('/place/<int:place_id>', methods=['GET', 'POST'])
def place_detail(place_id):
    place = Place.query.get_or_404(place_id)
    form = ReviewForm()
    
    if form.validate_on_submit():
        review = Review(
            place_id=place.id,
            rating=form.rating.data,
            comment=form.comment.data,
            author=form.author.data
        )
        db.session.add(review)
        db.session.commit()
        flash('Ваш отзыв добавлен!', 'success')
        return redirect(url_for('place_detail', place_id=place.id))
    
    return render_template('place_detail.html', place=place, form=form)

@app.route('/add_place', methods=['GET', 'POST'])
def add_place():
    form = PlaceForm()
    
    if form.validate_on_submit():
        place = Place(
            name=form.name.data,
            address=form.address.data,
            description=form.description.data,
            category=form.category.data,
            latitude=form.latitude.data,
            longitude=form.longitude.data
        )
        db.session.add(place)
        db.session.commit()
        
        # Обработка загруженных файлов
        if 'photo' in request.files:
            for file in request.files.getlist('photo'):
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    place_photo = PlacePhoto(place_id=place.id, filename=filename)
                    db.session.add(place_photo)
        
        db.session.commit()
        flash('Место успешно добавлено!', 'success')
        return redirect(url_for('index'))
    
    return render_template('add_place.html', form=form)

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)