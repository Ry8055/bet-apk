from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello from Vercel!'

@app.route('/api/test')
def test():
    return {'message': 'API working!'}

if __name__ == '__main__':
    app.run()