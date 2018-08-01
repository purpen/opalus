#!env/bin/python
from app import create_app, db
from flask_script import Manager, Server, Shell

app = create_app()
manager = Manager(app)

def _make_context():
    return dict(app=app, db=db)


manager.add_command("run", Server(host="127.0.0.1", port=8002))
manager.add_command("shell", Shell(make_context=_make_context))

if __name__ == '__main__':
    manager.run()
