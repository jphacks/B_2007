import tweepy
import urllib
import os
from flask import Flask, request, render_template, redirect, flash, session
from flask_sqlalchemy import SQLAlchemy

from datetime import timedelta
import logging
from requests_oauthlib import OAuth1Session
from urllib.parse import parse_qsl

from random import randint, seed

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
    due_date = db.Column(db.Date)
    monster_id = db.Column(db.Integer)
    is_finished = db.Column(db.Boolean, default=False)

@app.route('/')
def index():
    api = api_get()
    name =  api.me().name
    if not name:
        return redirect('twitter_auth')
    user_id = api.me().id
    unfinished = session.query(Assigment).filter(Assigment.is_finished==False, Assigment.user_id==user_id).order_by(Assigment.due_data).limit(3)
    finished =　sesscion.query(Assigment).filter(Assigment.is_finished==True,Assigment.user_id==user_id).order_by(desc(Assigment.due_data)).limit(4)
    """
    unfinishedの出力
    print([result.title for result in unfinished]) 出力はfor文使わんばエラーが出た気がする。
    finishedの出力
    print([result.is_finished for result in limit])
    """
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
        if request.form['tweet'] == True:
            api.update_with_media("{}.jpg".format(monster_id), status="新しいモンスター「{}」と戦います！ #AssignmentQuest".format(title))
        return redirect('/')
    else:
        return render_template('error.html')

@app.route('/finished', methods=['POST'])
    api = api_get()
    if request.form['id']:
        assignment = Assignment.query.filter_by(id=request.form["id"]).first()
        assignment.is_finished = True
        db_session.commit()
    if request.form['tweet'] == True:
        api.update_with_media("{}.jpg".format(assignment.monster_id), status="モンスター「{}」を蹴散らしました！ #AssignmentQuest".format(assignment.title))
    return redirect('/')


def api_get():
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
    return tweepy.API(auth)

@app.cli.command('initdb')
def initdb_command():
    db.create_all()