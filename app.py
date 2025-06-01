from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, emit
from flask_sqlalchemy import SQLAlchemy
import uuid


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# MySQL connection using XAMPP
# Make sure XAMPP MySQL is running and 'user_auth' database exists in phpMyAdmin
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/chats'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
socketio = SocketIO(app)
db = SQLAlchemy(app)

# Store active visitor IDs
active_visitors = set()

# Message model
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.String(100))
    sender = db.Column(db.String(20))  # 'Visitor' or 'Agent'
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

# Routes
@app.route('/widget')
def widget():
    return render_template('widget.html')

@app.route('/')
def dashboard():
    return render_template('dashboard.html', visitors=list(active_visitors))

# Socket.IO events
@socketio.on('join')
def on_join(data):
    visitor_id = data['visitor_id']
    join_room(visitor_id)
    
    # Track visitor in memory
    active_visitors.add(visitor_id)
    
    # Notify all dashboards to update visitor list
    emit('update_visitor_list', list(active_visitors), broadcast=True)

    print(f'{visitor_id} joined room')

@socketio.on('send_message')
def handle_send_message(data):
    visitor_id = data['visitor_id']
    sender = data['sender']
    message = data['message']

    # Save to DB
    new_msg = Message(visitor_id=visitor_id, sender=sender, message=message)
    db.session.add(new_msg)
    db.session.commit()

    # Send to the room
    emit('receive_message', {'sender': sender, 'message': message, 'visitor_id': visitor_id}, room=visitor_id)


@socketio.on('typing')
def on_typing(data):
    visitor_id = data['visitor_id']
    sender = data['sender']
    text = data.get('text', '')

    if sender == 'Agent':
        # Notify visitor their agent is typing
        emit('show_typing', {'sender': sender}, room=visitor_id)
    elif sender == 'Visitor':
        # Notify agent that visitor is typing
        # You can emit to all dashboard clients or specific logic here
        emit('visitor_typing', {'visitor_id': visitor_id, 'text': text}, broadcast=True)

@socketio.on('stop_typing')
def on_stop_typing(data):
    visitor_id = data['visitor_id']
    sender = data['sender']

    if sender == 'Agent':
        emit('hide_typing', room=visitor_id)
    elif sender == 'Visitor':
        emit('visitor_stop_typing', {'visitor_id': visitor_id}, broadcast=True)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)



