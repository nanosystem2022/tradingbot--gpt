from flask import Flask, render_template, request, jsonify, redirect, url_for
import json

app = Flask(__name__)

# load config.json
with open('config.json') as config_file:
    config = json.load(config_file)

@app.route('/')
def home():
    return render_template('settings.html', config=config)

@app.route('/update_config', methods=['POST'])
def update_config():
    global config
    config = request.form.to_dict()
    with open('config.json', 'w') as config_file:
        json.dump(config, config_file)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run()
