import tweepy
import urllib
import os
from flask import Flask, request, render_template, redirect, flash, make_response
from flask import session as sss
from flask_sqlalchemy import SQLAlchemy

from datetime import timedelta, datetime
import logging
from requests_oauthlib import OAuth1Session
from urllib.parse import parse_qsl

from random import randint, seed

from sqlalchemy import desc, create_engine
from sqlalchemy.orm import Session

app = Flask(__name__)
app.secret_key = os.environ['FLASK_SECRET_KEY']

AT = os.environ['ACCESS_TOKEN']
AS = os.environ['ACCESS_TOKEN_SECRET']
auth = tweepy.OAuthHandler(AT, AS)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
db = SQLAlchemy(app)

class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(64))
    user_id = db.Column(db.Integer)
    due_date = db.Column(db.Date)
    monster_id = db.Column(db.Integer)
    is_finished = db.Column(db.Boolean, default=False)

    def __init__(self, title, user_id, due_date, monster_id):
        self.title = title
        self.user_id = user_id
        self.due_date = due_date
        self.monster_id = monster_id

@app.route('/')
def index():
    api = api_get()
    if not api:
        return redirect('twitter_auth')
    name =  api.me().name
    user_id = api.me().id
    engine = create_engine(os.environ['PG_CREDENTIAL'])

    # Sessionインスタンスの生成
    session = Session(
        autocommit = False,
        autoflush = True,
        bind = engine)
    unfinished = session.query(Assignment).filter(Assignment.is_finished==False, Assignment.user_id==user_id).order_by(Assignment.due_date).limit(3)
    finished =session.query(Assignment).filter(Assignment.is_finished==False, Assignment.user_id==user_id).order_by(Assignment.due_date.desc()).limit(3)
    return render_template('ASSIGNMENT_QUEST.html', name=name, unfinished=unfinished, finished=finished)

@app.route('/twitter_auth', methods=['GET'])
def twitter_auth():
    try:
        # 連携アプリ認証用の URL を取得
        redirect_url = auth.get_authorization_url()
        # 認証後に必要な request_token を session に保存
        sss['request_token'] = auth.request_token
        return redirect(redirect_url)
    except tweepy.TweepError as e:
        logging.error(str(e))
        return redirect("https://www.google.com")

@app.route('/callback')
def callback():
    try:
        token = request.args.get('oauth_token', '')
        verifier = request.args.get('oauth_verifier', '')
        max_age = 60 * 60 * 24
        expires = int(datetime.now().timestamp()) + max_age
        response = make_response(redirect('/'))
        response.set_cookie('token', value=token, max_age=max_age, expires=expires)
        response.set_cookie('verifier', value=verifier, max_age=max_age, expires=expires)
        return response
    except:
        return render_template("login-error.html")



@app.route('/register', methods=['POST'])
def register():
    api = api_get()
    if request.form['title'] and request.form['due_date']:
        title = request.form['title']
        due_date = request.form['due_date']
        seed(title + due_date)
        random_num = randint(1, 100)
        monster_id = 0 if random_num > 60 else 1 if 30 < random_num < 60 else 2 if 15 < random_num < 30 else 3 if 5 < random_num < 15 else 4
        user_id = api.me().id
        newAssignment = Assignment(title, user_id, due_date, monster_id)
        db.session.add(newAssignment)
        db.session.commit()
        if request.form['tweet'] == "tweet":
            api.update_with_media("{}.png".format(monster_id), status="新しいモンスター「{}」と戦います！ #AssignmentQuest".format(title))

        return redirect('/')
    else:
        return render_template('login-error.html')

@app.route('/finished', methods=['POST'])
def finished():
    api = api_get()
    if request.form['id']:
        assignment = Assignment.query.filter_by(id=request.form["id"]).first()
        assignment.is_finished = True
        db_session.commit()
    if request.form['tweet'] == 'tweet':
        api.update_with_media("{}.png".format(assignment.monster_id), status="モンスター「{}」を蹴散らしました！ #AssignmentQuest".format(assignment.title))
    return redirect('/')


def api_get():
    token = request.cookies.get('token', None)
    verifier = request.cookies.get('verifier', None)
    if token is None or verifier is None:
        return False  # 未認証ならFalseを返す
    auth.request_token = token
    try:
        auth.get_access_token(verifier)
    except tweepy.TweepError as e:
        logging.error(str(e))
        print("error at 130")
        return 0
    return tweepy.API(auth)

@app.cli.command('initdb')
def initdb_command():
    db.create_all()
