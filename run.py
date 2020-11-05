import tweepy
import urllib
import os
from flask import Flask, request, render_template, redirect, flash, session
from flask_sqlalchemy import SQLAlchemy

from datetime import timedelta
import logging
from requests_oauthlib import OAuth1Session
from urllib.parse import parse_qsl


app = Flask(__name__)
app.secret_key = os.environ['FLASK_SECRET_KEY']

AT = os.environ['ACCESS_TOKEN']
AS = os.environ['ACCESS_TOKEN_SECRE']
auth = tweepy.OAuthHandler(AT, AS)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:パスワード@localhost/task"
db = SQLAlchemy(app)

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64))
    user_id = db.Column(db.Integer)

    monster_id = db.Column(db.Integer)
    monster_color = db.Column(db.String(64))
    is_finished = db.Column(db.Boolean)

@app.route('/')
def index():
    name, id = whoami()
    #SQLAlchemyを使ってassignmentsにログインしてるユーザーの
    assignments = {}
    return render_template('index.html', name=name, assignments=assignments)

@app.route('/twitter_auth', methods=['GET'])
def twitter_auth():
    try:
        # 連携アプリ認証用の URL を取得
        redirect_url = auth.get_authorization_url()
        # 認証後に必要な request_token を session に保存
        session['request_token'] = auth.request_token
    except tweepy.TweepError, e:
        logging.error(str(e))

    # リダイレクト
    return redirect(redirect_url)


@app.route('/callback')
def callback():
    try:
        token = request.values.get('oauth_token', '')
        verifier = request.values.get('oauth_verifier', '')
        #flash('認証に成功しました。')
        return render_template("index.html", token=token, verifier=verifier)
    except:
        return render_template("error.html")


@app.route('/register', methods=['POST'])
def register():
    token = session.pop('request_token', None)
    verifier = request.args.get('oauth_verifier')
    if token is None or verifier is None:
        return False  # 未認証ならFalseを返す
    auth.request_token = token
    try:
        auth.get_access_token(verifier)
    except tweepy.TweepError, e:
        logging.error(str(e))
        return {}
    api = tweepy.API(auth)
    api.update_status("テストツイート from Tweepy on Flask")
    if request.form['title'] and request.form['content'] and request.files['image']:
        monster_id = len(request.form['title']) % 5
        newAssignment = Assignment()
        db.session.add(newAssignment)
        db.session.commit()
        if request.form['tweet_true'] == True:
            api.update_with_media(filename, status="新しいモンスター{}と戦います。".format(request.form['title']))
        return redirect('/')

    else:
        return render_template('error.html')

def whoami():
    token = session.pop('request_token', None)
    verifier = request.args.get('oauth_verifier')
    if token is None or verifier is None:
        return False  # 未認証ならFalseを返す
    auth.request_token = token
    try:
        auth.get_access_token(verifier)
    except tweepy.TweepError, e:
        logging.error(str(e))
        return {}
    api = tweepy.API(auth)
    me = api.me()
    return me.name, me.id


@app.cli.command('initdb')
def initdb_command():
    db.create_all()
