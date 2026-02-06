from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime, timedelta
import secrets

app = Flask(__name__)
app.secret_key = 'ganti-dengan-key-rahasia-anda'

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'psd', 'pdf', 'ai'}
MAX_FILE_SIZE = 50 * 1024 * 1024

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- DATABASE HELPER ---
def get_db_connection():
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # Create Tables Safely
    queries = [
        '''CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            client_name TEXT NOT NULL,
            client_email TEXT NOT NULL,
            designer_name TEXT,
            status TEXT DEFAULT 'in_progress',
            progress INTEGER DEFAULT 0,
            deadline DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            access_token TEXT UNIQUE NOT NULL,
            max_revisions INTEGER DEFAULT 3,
            used_revisions INTEGER DEFAULT 0
        )''',
        '''CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT,
            version INTEGER DEFAULT 1,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_latest BOOLEAN DEFAULT 1,
            is_downloadable BOOLEAN DEFAULT 0,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            comment TEXT NOT NULL,
            revision_number INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            activity_type TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        )'''
    ]
    
    for q in queries:
        conn.execute(q)
        
    conn.commit()
    conn.close()

def seed_data():
    """Isi data dummy jika database kosong"""
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects'")
        if not cursor.fetchone():
            init_db()
            
        if conn.execute('SELECT COUNT(*) FROM projects').fetchone()[0] > 0:
            conn.close()
            return
    except:
        init_db()

    print("Seeding data...")
    token = 'demo-token-123'
    deadline = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
    
    conn.execute('''
        INSERT INTO projects (title, description, client_name, client_email, status, progress, deadline, access_token, max_revisions, used_revisions) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', ('Thumbnail YouTube - Gaming', 'Project Demo Sidang', 'Riko Gaming', 'riko@example.com', 'needs_revision', 80, deadline, token, 3, 2))
    
    pid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.execute('INSERT INTO activities (project_id, activity_type, description) VALUES (?, ?, ?)', (pid, 'project_start', 'Proyek dimulai'))
    conn.execute('INSERT INTO feedbacks (project_id, comment, revision_number) VALUES (?, ?, ?)', (pid, 'Warna kurang cerah', 1))
    
    conn.commit()
    conn.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# --- ROUTES: FREELANCER DASHBOARD ---
@app.route('/')
@app.route('/freelancer')
def freelancer_dashboard():
    status_filter = request.args.get('status')
    conn = get_db_connection()

    base_query = '''
        SELECT p.*,
               COUNT(DISTINCT f.id) as total_files,
               (SELECT COUNT(*) FROM feedbacks WHERE project_id = p.id) as total_feedbacks,
               (SELECT comment FROM feedbacks WHERE project_id = p.id ORDER BY created_at DESC LIMIT 1) as latest_comment,
               (SELECT created_at FROM feedbacks WHERE project_id = p.id ORDER BY created_at DESC LIMIT 1) as latest_comment_date
        FROM projects p
        LEFT JOIN files f ON p.id = f.project_id
    '''

    if status_filter == 'completed':
        where_clause = "WHERE p.status = 'completed'"
        page_title = "Archived Design"
    elif status_filter == 'needs_revision':
        where_clause = "WHERE p.status = 'needs_revision'"
        page_title = "Revision Pending List"
    else:
        where_clause = "WHERE p.status != 'completed'"
        page_title = "Active Project"

    final_query = f"{base_query} {where_clause} GROUP BY p.id ORDER BY p.updated_at DESC"
    
    try:
        raw_projects = conn.execute(final_query).fetchall()
        
        # Proses projects
        projects = []
        for p in raw_projects:
            p_dict = dict(p)
            if p_dict['deadline']:
                try:
                    deadline_date = datetime.strptime(p_dict['deadline'], '%Y-%m-%d')
                    delta = deadline_date - datetime.now()
                    p_dict['days_left'] = delta.days
                except ValueError:
                    p_dict['days_left'] = 0 
            else:
                p_dict['days_left'] = 0
            projects.append(p_dict)
        
        active_cnt = conn.execute("SELECT COUNT(*) FROM projects WHERE status != 'completed'").fetchone()[0]
        completed_cnt = conn.execute("SELECT COUNT(*) FROM projects WHERE status = 'completed'").fetchone()[0]
        revision_cnt = conn.execute("SELECT COUNT(*) FROM projects WHERE status = 'needs_revision'").fetchone()[0]
    except sqlite3.OperationalError:
        init_db()
        seed_data()
        projects = []
        active_cnt = 0
        completed_cnt = 0
        revision_cnt = 0

    stats = {
        'active_projects': active_cnt,
        'completed_this_month': completed_cnt,
        'pending_revisions': revision_cnt,
        'avg_completion_time': '2.5 days'
    }

    conn.close()
    return render_template('freelancer_dashboard.html', 
                           projects=projects, stats=stats, 
                           current_filter=status_filter, page_title=page_title)

@app.route('/create-project', methods=['POST'])
def create_project():
    conn = get_db_connection()
    title = request.form.get('title')
    client_name = request.form.get('client_name')
    description = request.form.get('description')
    deadline = request.form.get('deadline')
    designer_name = request.form.get('designer_name') 

    if not title or not client_name or not deadline:
        flash('Data tidak lengkap!', 'error')
        return redirect(url_for('freelancer_dashboard'))

    token = secrets.token_urlsafe(32)
    try:
        conn.execute('''
            INSERT INTO projects (title, client_name, client_email, description, deadline, access_token, status, progress, designer_name) 
            VALUES (?, ?, ?, ?, ?, ?, 'in_progress', 0, ?)
        ''', (title, client_name, 'client@mail.com', description, deadline, token, designer_name))
        
        pid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.execute('INSERT INTO activities (project_id, activity_type, description) VALUES (?, ?, ?)', (pid, 'project_start', f'Proyek dibuat untuk {client_name}'))
        conn.commit()
        flash('Project successfully created', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('freelancer_dashboard'))


# --- ROUTES: PROJECT DETAIL & ACTIONS ---
@app.route('/project/<int:project_id>')
def freelancer_project_detail(project_id):
    conn = get_db_connection()
    try:
        project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()

        if not project:
            conn.close()
            return redirect(url_for('freelancer_dashboard'))

        files = conn.execute('SELECT * FROM files WHERE project_id = ? ORDER BY version DESC, uploaded_at DESC', (project_id,)).fetchall()
        feedbacks = conn.execute('SELECT * FROM feedbacks WHERE project_id = ? ORDER BY created_at DESC', (project_id,)).fetchall()
        activities = conn.execute('SELECT * FROM activities WHERE project_id = ? ORDER BY created_at DESC', (project_id,)).fetchall()
    except:
        # Fallback jika error
        conn.close()
        return redirect(url_for('freelancer_dashboard'))

    conn.close()
    return render_template('project_detail.html', project=project, files=files, feedbacks=feedbacks, activities=activities)

@app.route('/upload/<int:project_id>', methods=['POST'])
def upload_file(project_id):
    if 'file' not in request.files: return redirect(url_for('freelancer_project_detail', project_id=project_id))
    
    file = request.files['file']
    is_final = request.form.get('is_final') # Checkbox input
    
    if file.filename == '' or not allowed_file(file.filename):
        flash('File tidak valid', 'error')
        return redirect(url_for('freelancer_project_detail', project_id=project_id))
    
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    saved_filename = f"{timestamp}_{filename}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], saved_filename))
    
    conn = get_db_connection()
    # Logika Status Download
    is_downloadable = 1 if is_final else 0
    
    last_ver = conn.execute('SELECT MAX(version) as max_ver FROM files WHERE project_id = ?', (project_id,)).fetchone()['max_ver'] or 0
    new_ver = last_ver + 1
    
    conn.execute('UPDATE files SET is_latest = 0 WHERE project_id = ?', (project_id,))
    conn.execute('''
        INSERT INTO files (project_id, filename, file_path, file_type, version, is_downloadable, is_latest) 
        VALUES (?, ?, ?, ?, ?, ?, 1)
    ''', (project_id, saved_filename, os.path.join(app.config['UPLOAD_FOLDER'], saved_filename), file.filename.split('.')[-1], new_ver, is_downloadable))
    
    conn.execute('INSERT INTO activities (project_id, activity_type, description) VALUES (?, ?, ?)', (project_id, 'file_upload', f'Upload: {filename}'))
    conn.execute('UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = ?', (project_id,))
    
    conn.commit()
    conn.close()
    flash('File Has Been Uploaded', 'success')
    return redirect(url_for('freelancer_project_detail', project_id=project_id))

@app.route('/delete-file/<int:file_id>', methods=['POST'])
def delete_file(file_id):
    conn = get_db_connection()
    file = conn.execute('SELECT * FROM files WHERE id = ?', (file_id,)).fetchone()
    
    if file:
        pid = file['project_id']
        try:
            if os.path.exists(file['file_path']): os.remove(file['file_path'])
        except: pass
        
        conn.execute('DELETE FROM files WHERE id = ?', (file_id,))
        conn.execute('INSERT INTO activities (project_id, activity_type, description) VALUES (?, ?, ?)', (pid, 'file_deleted', 'File Deleted'))
        conn.commit()
        conn.close()
        flash('File Deleted.', 'success')
        return redirect(url_for('freelancer_project_detail', project_id=pid))
    
    conn.close()
    return redirect(url_for('freelancer_dashboard'))

@app.route('/toggle-lock/<int:file_id>', methods=['POST'])
def toggle_file_lock(file_id):
    conn = get_db_connection()
    file = conn.execute('SELECT project_id, is_downloadable FROM files WHERE id = ?', (file_id,)).fetchone()
    
    if file:
        pid = file['project_id']
        new_status = 0 if file['is_downloadable'] else 1
        conn.execute('UPDATE files SET is_downloadable = ? WHERE id = ?', (new_status, file_id))
        conn.execute('INSERT INTO activities (project_id, activity_type, description) VALUES (?, ?, ?)', (pid, 'file_update', 'File access status changed'))
        conn.commit()
        conn.close()
        flash('File access status updated', 'success')
        return redirect(url_for('freelancer_project_detail', project_id=pid))
    
    conn.close()
    return redirect(url_for('freelancer_dashboard'))

@app.route('/edit-project/<int:project_id>', methods=['POST'])
def edit_project(project_id):
    conn = get_db_connection()
    try:
        conn.execute('''
            UPDATE projects SET title = ?, description = ?, deadline = ?, status = ?, designer_name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
        ''', (
            request.form.get('title'), 
            request.form.get('description'), 
            request.form.get('deadline'), 
            request.form.get('status'), 
            request.form.get('designer_name'),
            project_id
        ))
        conn.execute('INSERT INTO activities (project_id, activity_type, description) VALUES (?, ?, ?)', (project_id, 'project_update', 'Info proyek diperbarui'))
        conn.commit()
        flash('Proyek diperbarui!', 'success')
    except Exception as e: 
        flash(f'Gagal update: {e}', 'error')
    finally:
        conn.close()
    return redirect(url_for('freelancer_project_detail', project_id=project_id))

@app.route('/delete-project/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    conn = get_db_connection()
    files = conn.execute('SELECT file_path FROM files WHERE project_id = ?', (project_id,)).fetchall()
    try:
        for f in files:
            try: 
                if os.path.exists(f['file_path']): os.remove(f['file_path'])
            except: pass
        conn.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        conn.commit()
        flash('Proyek dihapus permanen.', 'success')
    except:
        flash('Gagal menghapus.', 'error')
    finally:
        conn.close()
    return redirect(url_for('freelancer_dashboard'))

@app.route('/finish-project/<int:project_id>', methods=['POST'])
def finish_project(project_id):
    conn = get_db_connection()
    conn.execute("UPDATE projects SET status = 'completed' WHERE id = ?", (project_id,))
    conn.execute("INSERT INTO activities (project_id, activity_type, description) VALUES (?, 'completed', 'Project Archived')", (project_id,))
    conn.commit()
    conn.close()
    flash('Project completed and archived', 'success')
    return redirect(url_for('freelancer_dashboard'))


# --- ROUTES: CLIENT SIDE ---
@app.route('/client/<token>')
def client_dashboard(token):
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE access_token = ?', (token,)).fetchone()
    if not project:
        conn.close()
        return "Link tidak valid", 404

    files = conn.execute('SELECT * FROM files WHERE project_id = ? ORDER BY version DESC, uploaded_at DESC', (project['id'],)).fetchall()
    feedbacks = conn.execute('SELECT * FROM feedbacks WHERE project_id = ? ORDER BY created_at DESC', (project['id'],)).fetchall()
    activities = conn.execute('SELECT * FROM activities WHERE project_id = ? ORDER BY created_at DESC LIMIT 10', (project['id'],)).fetchall()
    
    conn.close()
    return render_template('client_dashboard.html', project=project, files=files, feedbacks=feedbacks, activities=activities)

@app.route('/feedback/<token>', methods=['POST'])
def submit_feedback(token):
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE access_token = ?', (token,)).fetchone()
    if not project:
        conn.close()
        return "Error", 404

    comment = request.form.get('comment')
    action = request.form.get('action')

    if action == 'revision':
        if project['used_revisions'] >= project['max_revisions']:
            flash('Kuota revisi habis', 'error')
        else:
            conn.execute('INSERT INTO feedbacks (project_id, comment, revision_number) VALUES (?, ?, ?)', (project['id'], comment, project['used_revisions'] + 1))
            conn.execute("UPDATE projects SET used_revisions = used_revisions + 1, status = 'needs_revision', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (project['id'],))
            conn.execute('INSERT INTO activities (project_id, activity_type, description) VALUES (?, ?, ?)', (project['id'], 'feedback', 'Client minta revisi'))
            flash('Feedback Sent', 'success')

    elif action == 'approve':
        conn.execute("UPDATE projects SET status = 'finalizing', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (project['id'],))
        conn.execute('INSERT INTO activities (project_id, activity_type, description) VALUES (?, ?, ?)', (project['id'], 'approved', 'Desain disetujui'))
        flash('Assigned Design as Approved, please wait for final file', 'success')
    
    conn.commit()
    conn.close()
    return redirect(url_for('client_dashboard', token=token))

# --- SYSTEM UTILS ---
@app.route('/fix-db')
def fix_database_structure():
    conn = get_db_connection()
    try:
        conn.execute('ALTER TABLE files ADD COLUMN is_downloadable BOOLEAN DEFAULT 0')
        conn.commit()
        msg = "Database Updated."
    except:
        msg = "Database Up to Date."
    finally:
        conn.close()
    return msg

if __name__ == '__main__':
    if not os.path.exists('database.db'):
        init_db()
        seed_data()
    app.run(debug=True, host='0.0.0.0', port=5000)