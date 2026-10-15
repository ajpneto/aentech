# app/main/views.py
from flask import current_app, render_template, redirect, url_for, flash, request, abort, session, g
from functools import wraps
from slugify import slugify
from app import db
from app.models import User, Post, Category, Comment, Tutorial, TutorialPost
from app.forms import PostForm, CommentForm, CategoryForm, TutorialForm
from app.main import blueprint
from app.seo import post_seo, category_seo, tutorial_seo, meta_excerpt, absolute_url, site_base_url
from sqlalchemy import or_
from app import get_config
from datetime import datetime
import os

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('auth.login', next=request.path))
        user = User.query.get(user_id)
        if not user or not user.is_administrator():
            flash('Acesso negado. Apenas o administrador pode realizar esta ação.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def get_default_user():
    """Helper to get a default user for posts/comments since auth is removed"""
    user = User.query.first()
    if not user:
        # Create a default user if none exists
        user = User(username='admin', email='admin@example.com')
        db.session.add(user)
        db.session.commit()
    return user

@blueprint.route('/')
@blueprint.route('/home')
def index():
    """Home page showing landing page with recent posts"""
    recent_posts = Post.query.filter_by(is_published=True)\
        .order_by(Post.created_at.desc())\
        .limit(3).all()
    return render_template('main/index.html', recent_posts=recent_posts)

@blueprint.route('/posts')
def posts_list():
    """Blog page showing all published posts"""
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter_by(is_published=True)\
        .order_by(Post.created_at.desc())\
        .paginate(page=page, per_page=get_config('POSTS_PER_PAGE', 10))
    categories = Category.query.all()
    g.seo = {'pagination': posts}
    return render_template('main/posts.html', posts=posts, cats=categories, title='Últimas Postagens')

@blueprint.route('/survey')
def survey():
    """Render the STEM survey submission data"""
    import json
    json_path = os.path.join(current_app.root_path, '..', 'stem_survey_serialized_submission.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            survey_data = json.load(f)
    except FileNotFoundError:
        abort(404, description="Arquivo de dados da pesquisa não encontrado.")
    return render_template('main/survey.html', survey=survey_data)

@blueprint.route('/chemistry')
def chemistry():
    """Render the chemistry page with recent posts from Química category"""
    quimica_cat = Category.query.filter((Category.slug == 'quimica') | (Category.name.ilike('Química'))).first()
    if quimica_cat:
        recent_posts = Post.query.filter_by(is_published=True)\
            .join(Post.categories)\
            .filter(Category.id == quimica_cat.id)\
            .order_by(Post.created_at.desc())\
            .limit(3).all()
    else:
        recent_posts = []
    return render_template('main/chemistry.html', recent_posts=recent_posts)

@blueprint.route('/chemistry/posts')
def chemistry_posts():
    """Exclusive route for Chemistry posts"""
    page = request.args.get('page', 1, type=int)
    quimica_cat = Category.query.filter((Category.slug == 'quimica') | (Category.name.ilike('Química'))).first()
    if quimica_cat:
        posts = Post.query.filter_by(is_published=True)\
            .join(Post.categories)\
            .filter(Category.id == quimica_cat.id)\
            .order_by(Post.created_at.desc())\
            .paginate(page=page, per_page=get_config('POSTS_PER_PAGE', 10))
    else:
        posts = Post.query.filter(False).paginate(page=page, per_page=10)

    g.seo = {'pagination': posts}
    return render_template('main/chemistry_posts.html', posts=posts, category=quimica_cat, title='Artigos de Química')


@blueprint.route('/post/<slug>', methods=['GET', 'POST'])
def post_detail(slug):
    """View individual post with comments"""
    post = Post.query.filter_by(slug=slug).first_or_404()
    form = CommentForm()
    
    if form.validate_on_submit():
        user_id = session.get('user_id')
        user = User.query.get(user_id) if user_id else get_default_user()
        comment = Comment(
            content=form.content.data,
            post_id=post.id,
            user_id=user.id,
            is_approved=True
        )
        db.session.add(comment)
        db.session.commit()
        flash('Sua anotação foi salva!', 'success')
        return redirect(url_for('main.post_detail', slug=slug))
    
    comments = Comment.query.filter_by(post_id=post.id)        .order_by(Comment.created_at.desc()).all()

    g.seo = post_seo(post)
    return render_template('main/post.html', post=post, form=form, comments=comments)

@blueprint.route('/category/<slug>')
def category_posts(slug):
    """View posts by category"""
    category = Category.query.filter_by(slug=slug).first_or_404()
    categories = Category.query.all()
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter_by(is_published=True)        .join(Post.categories)        .filter(Category.id == category.id)        .order_by(Post.created_at.desc())        .paginate(page=page, per_page=5)
    g.seo = category_seo(category, pagination=posts)
    return render_template('main/posts.html', posts=posts, category=category, cats=categories, 
                          title=f'Posts em "{category.name}"')

@blueprint.route('/create', methods=['GET', 'POST'])
@admin_required
def create_post():
    """Create a new post"""
    all_categories = Category.query.all()
    form = PostForm()
    form.categories.choices = [(cat.id, cat.name) for cat in all_categories]
    
    if form.validate_on_submit():
        if not form.slug.data:
            form.slug.data = slugify(form.title.data)
        
        existing_post = Post.query.filter_by(slug=form.slug.data).first()
        if existing_post:
            form.slug.errors.append('Este slug já está em uso.')
            return render_template('main/create_post.html', form=form, categories=all_categories)
        
        user = User.query.get(session['user_id'])
        post = Post(
            title=form.title.data,
            slug=form.slug.data,
            content=form.content.data,
            excerpt=form.excerpt.data or form.content.data[:297] + '...',
            is_published=form.is_published.data,
            user_id=user.id
        )
        
        submitted_category_ids = request.form.getlist('categories')
        for category_id in submitted_category_ids:
            category = Category.query.get(category_id)
            if category:
                post.categories.append(category)
        
        db.session.add(post)
        db.session.commit()
        flash('Post criado com sucesso!', 'success')
        return redirect(url_for('main.post_detail', slug=post.slug))
    
    return render_template('main/create_post.html', form=form, categories=all_categories, title='Criar Novo Post')

@blueprint.route('/post/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_post(id):
    post = Post.query.get_or_404(id)
    all_categories = Category.query.all()
    form = PostForm(obj=post)
    form.categories.choices = [(cat.id, cat.name) for cat in all_categories]
    form.categories.data = [cat.id for cat in post.categories]
    
    if form.validate_on_submit():
        if form.slug.data != post.slug:
            existing_post = Post.query.filter_by(slug=form.slug.data).first()
            if existing_post and existing_post.id != post.id:
                form.slug.errors.append('Este slug já está em uso.')
                return render_template('main/edit_post.html', form=form, post=post, categories=all_categories)
        
        post.title = form.title.data
        post.slug = form.slug.data
        post.content = form.content.data
        post.excerpt = form.excerpt.data or form.content.data[:297] + '...'
        post.is_published = form.is_published.data
        
        submitted_category_ids = request.form.getlist('categories')
        post.categories = []
        for category_id in submitted_category_ids:
            category = Category.query.get(category_id)
            if category:
                post.categories.append(category)
        
        db.session.commit()
        flash('Post atualizado com sucesso!', 'success')
        return redirect(url_for('main.post_detail', slug=post.slug))
    
    return render_template('main/edit_post.html', form=form, post=post, categories=all_categories)

@blueprint.route('/post/<int:id>/delete', methods=['POST'])
@admin_required
def delete_post(id):
    """Delete a post"""
    post = Post.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    flash('Post excluído com sucesso!', 'success')
    return redirect(url_for('main.index'))

@blueprint.route('/search')
def search():
    """Search posts"""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    categories = Category.query.all()
    
    if query:
        posts = Post.query.filter(
            or_(
                Post.title.ilike(f'%{query}%'),
                Post.content.ilike(f'%{query}%'),
                Post.excerpt.ilike(f'%{query}%')
            )
        ).order_by(Post.created_at.desc())         .paginate(page=page, per_page=10)
    else:
        posts = Post.query.order_by(Post.created_at.desc())            .paginate(page=page, per_page=10)

    if query:
        g.seo = {
            'title': f'Busca: "{query}"',
            'description': f'Resultados de busca para "{query}" na plataforma AENTECH: artigos, tutoriais e ferramentas de ciência e tecnologia.',
            'keywords': f'{query}, busca, artigos, AENTECH',
            'robots': 'noindex, follow',
            'pagination': posts,
        }
    else:
        g.seo = {'robots': 'noindex, follow', 'pagination': posts}
    return render_template('main/posts.html', posts=posts, query=query, cats=categories, title=f'Busca: "{query}"')

@blueprint.route('/my-posts')
@admin_required
def my_posts():
    """Manage all posts"""
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.created_at.desc())        .paginate(page=page, per_page=10)
    return render_template('main/posts.html', posts=posts, title='Gerenciar Postagens')

@blueprint.route('/drafts')
@admin_required
def drafts():
    """View drafts"""
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter_by(is_published=False)        .order_by(Post.created_at.desc())        .paginate(page=page, per_page=10)
    return render_template('main/posts.html', posts=posts, title='Rascunhos')

@blueprint.route('/categories', methods=['GET', 'POST'])
@admin_required
def manage_categories():
    """Manage categories"""
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            slug=form.slug.data or slugify(form.name.data),
            description=form.description.data
        )
        db.session.add(category)
        db.session.commit()
        flash('Categoria criada com sucesso!', 'success')
        return redirect(url_for('main.manage_categories'))
    
    categories = Category.query.order_by(Category.name).all()
    return render_template('main/manage_categories.html', form=form, categories=categories)

@blueprint.route('/category/<int:id>/delete', methods=['POST'])
@admin_required
def delete_category(id):
    """Delete category"""
    category = Category.query.get_or_404(id)
    db.session.delete(category)
    db.session.commit()
    flash('Categoria excluída!', 'success')
    return redirect(url_for('main.manage_categories'))

# ============================================================================
# Tutorial Routes & CRUD
# ============================================================================

@blueprint.route('/tutoriais')
def tutorials_list():
    """Main tutorials page listing all tutorials"""
    tutorials = Tutorial.query.order_by(Tutorial.created_at.desc()).all()
    return render_template('main/tutorials.html', tutorials=tutorials)

@blueprint.route('/tutoriais/<identifier>')
def tutorial_detail(identifier):
    """Tutorial detail page listing ordered posts"""
    tutorial = None
    if identifier.isdigit():
        tutorial = Tutorial.query.get(int(identifier))
    if not tutorial:
        tutorial = Tutorial.query.filter_by(slug=identifier).first_or_404()

    posts = tutorial.ordered_posts
    g.seo = tutorial_seo(tutorial, posts)
    return render_template('main/tutorial_detail.html', tutorial=tutorial, posts=posts)

@blueprint.route('/admin/tutoriais')
@admin_required
def manage_tutorials():
    """Admin management page for tutorials"""
    tutorials = Tutorial.query.order_by(Tutorial.created_at.desc()).all()
    return render_template('main/manage_tutorials.html', tutorials=tutorials)

@blueprint.route('/tutoriais/novo', methods=['GET', 'POST'])
@admin_required
def create_tutorial():
    """Create a new tutorial"""
    form = TutorialForm()
    all_posts = Post.query.filter_by(is_published=True).order_by(Post.title.asc()).all()
    all_categories = Category.query.all()

    if form.validate_on_submit():
        slug = form.slug.data or slugify(form.title.data)
        existing = Tutorial.query.filter_by(slug=slug).first()
        if existing:
            form.slug.errors.append('Este slug já está em uso.')
            return render_template('main/create_tutorial.html', form=form, all_posts=all_posts, categories=all_categories)

        tutorial = Tutorial(
            title=form.title.data,
            slug=slug,
            description=form.description.data
        )
        db.session.add(tutorial)
        db.session.flush()

        selected_post_ids = request.form.getlist('selected_posts')
        for idx, post_id_str in enumerate(selected_post_ids):
            try:
                pid = int(post_id_str)
                order_val = request.form.get(f'order_{pid}', default=idx + 1, type=int)
                tp = TutorialPost(tutorial_id=tutorial.id, post_id=pid, order=order_val)
                db.session.add(tp)
            except (ValueError, TypeError):
                continue

        db.session.commit()
        flash('Tutorial criado com sucesso!', 'success')
        return redirect(url_for('main.tutorial_detail', identifier=tutorial.slug))

    return render_template('main/create_tutorial.html', form=form, all_posts=all_posts, categories=all_categories)

@blueprint.route('/tutoriais/<int:id>/editar', methods=['GET', 'POST'])
@admin_required
def edit_tutorial(id):
    """Edit an existing tutorial"""
    tutorial = Tutorial.query.get_or_404(id)
    form = TutorialForm(obj=tutorial)
    all_posts = Post.query.filter_by(is_published=True).order_by(Post.title.asc()).all()
    all_categories = Category.query.all()

    current_post_orders = {tp.post_id: tp.order for tp in tutorial.tutorial_posts}

    if form.validate_on_submit():
        new_slug = form.slug.data or slugify(form.title.data)
        if new_slug != tutorial.slug:
            existing = Tutorial.query.filter_by(slug=new_slug).first()
            if existing and existing.id != tutorial.id:
                form.slug.errors.append('Este slug já está em uso.')
                return render_template('main/edit_tutorial.html', form=form, tutorial=tutorial, all_posts=all_posts, current_post_orders=current_post_orders, categories=all_categories)

        tutorial.title = form.title.data
        tutorial.slug = new_slug
        tutorial.description = form.description.data

        TutorialPost.query.filter_by(tutorial_id=tutorial.id).delete()

        selected_post_ids = request.form.getlist('selected_posts')
        for idx, post_id_str in enumerate(selected_post_ids):
            try:
                pid = int(post_id_str)
                order_val = request.form.get(f'order_{pid}', default=idx + 1, type=int)
                tp = TutorialPost(tutorial_id=tutorial.id, post_id=pid, order=order_val)
                db.session.add(tp)
            except (ValueError, TypeError):
                continue

        db.session.commit()
        flash('Tutorial atualizado com sucesso!', 'success')
        return redirect(url_for('main.tutorial_detail', identifier=tutorial.slug))

    return render_template('main/edit_tutorial.html', form=form, tutorial=tutorial, all_posts=all_posts, current_post_orders=current_post_orders, categories=all_categories)

@blueprint.route('/tutoriais/<int:id>/excluir', methods=['POST'])
@admin_required
def delete_tutorial(id):
    """Delete a tutorial"""
    tutorial = Tutorial.query.get_or_404(id)
    db.session.delete(tutorial)
    db.session.commit()
    flash('Tutorial excluído com sucesso!', 'success')
    return redirect(url_for('main.tutorials_list'))


# ============================================================================
# SEO crawling endpoints
# ============================================================================

@blueprint.route('/robots.txt')
def robots_txt():
    """Serve the robots.txt file with a reference to the dynamic sitemap."""
    sitemap_url = absolute_url('/sitemap.xml')
    body = render_template('robots.txt', sitemap_url=sitemap_url)
    return body, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@blueprint.route('/sitemap.xml')
def sitemap_xml():
    """Generate a dynamic XML sitemap of the public pages, posts, categories and tutorials."""
    pages = []
    now = datetime.utcnow()

    static_pages = [
        ('main.index', 1.0, 'daily'),
        ('main.posts_list', 0.9, 'daily'),
        ('main.chemistry', 0.8, 'weekly'),
        ('main.chemistry_posts', 0.7, 'weekly'),
        ('main.survey', 0.7, 'monthly'),
        ('main.tutorials_list', 0.8, 'weekly'),
    ]
    for endpoint, priority, freq in static_pages:
        loc = site_base_url() + '/' if endpoint == 'main.index' else absolute_url(url_for(endpoint))
        pages.append({
            'loc': loc,
            'lastmod': now,
            'changefreq': freq,
            'priority': priority,
        })

    for post in Post.query.filter_by(is_published=True).order_by(Post.updated_at.desc()).all():
        pages.append({
            'loc': absolute_url(url_for('main.post_detail', slug=post.slug)),
            'lastmod': post.updated_at or post.created_at,
            'changefreq': 'monthly',
            'priority': 0.8,
        })

    for category in Category.query.order_by(Category.name).all():
        pages.append({
            'loc': absolute_url(url_for('main.category_posts', slug=category.slug)),
            'lastmod': now,
            'changefreq': 'weekly',
            'priority': 0.6,
        })

    for tutorial in Tutorial.query.order_by(Tutorial.updated_at.desc()).all():
        pages.append({
            'loc': absolute_url(url_for('main.tutorial_detail', identifier=tutorial.slug)),
            'lastmod': tutorial.updated_at or tutorial.created_at,
            'changefreq': 'monthly',
            'priority': 0.7,
        })

    body = render_template('sitemap.xml', pages=pages)
    return body, 200, {'Content-Type': 'application/xml; charset=utf-8'}

