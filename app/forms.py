from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField, TextAreaField, SelectMultipleField
from wtforms.validators import DataRequired, Optional, Length
from app.models import Category

class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    slug = StringField('Slug', validators=[Optional(), Length(max=200)])
    content = TextAreaField('Content', validators=[DataRequired()])
    excerpt = TextAreaField('Excerpt', validators=[Optional(), Length(max=300)])
    categories = SelectMultipleField('Categories', coerce=int, choices=[])
    is_published = BooleanField('Publish', default=True)
    submit = SubmitField('Submit')


class CategoryForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=50)])
    slug = StringField('Slug', validators=[DataRequired(), Length(max=50)])
    description = StringField('Description', validators=[Length(max=200)])
    submit = SubmitField('Save Category')


class CommentForm(FlaskForm):
    content = TextAreaField('Comment', validators=[DataRequired()])
    submit = SubmitField('Post Comment')

class TutorialForm(FlaskForm):
    title = StringField('Título', validators=[DataRequired(), Length(max=200)])
    slug = StringField('Slug', validators=[Optional(), Length(max=200)])
    description = TextAreaField('Descrição', validators=[Optional()])
    submit = SubmitField('Salvar Tutorial')

