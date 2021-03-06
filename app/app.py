#Flaskとrender_template（HTMLを表示させるための関数）をインポート
from flask import Flask,render_template, request, session,redirect,url_for
from models.models import PaperContent, User
from models.database import db_session
from datetime import datetime
from app import key
from hashlib import sha256
from app.scraper import url2list
from sqlalchemy import func
from app.ML import learning

#Flaskオブジェクトの生成
app = Flask(__name__)
app.secret_key = key.SECRET_KEY

@app.route("/")
@app.route("/index")
def index():
    if "user_name" in session:
        name = session["user_name"]
        #all_contents = db_session.query(PaperContent.title_en, PaperContent.date).all()
        latest = db_session.query(func.max(PaperContent.date), PaperContent.url).all()#最新日付とそのURLを取得
        latest_contents = db_session.query(PaperContent.title_en, PaperContent.title_jp, PaperContent.abst_en, PaperContent.abst_jp, 
        PaperContent.date, PaperContent.id, PaperContent.prob, PaperContent.sol, PaperContent.app, PaperContent.prob_est,
        PaperContent.sol_est, PaperContent.app_est).filter(PaperContent.url == latest[0][1]).all()#最新URLと同じURLをDBから引っ張ってくる
        return render_template("index.html",name=name,all_contents=latest_contents)
    else:
        return redirect(url_for("top"))

@app.route("/url",methods=["post"])
def url():
    url = request.form["url"]
    print(url)
    title_en, abst_en_ls, title_jp, abst_jp_ls = url2list(url)
    ### 課題、解決法、応用を初期化
    prob, sol, app, prob_est, sol_est, app_est  = 0, 0, 0, 0, 0, 0 

    ### DBにデータ保存
    abst_en = abst_en_ls
    abst_jp = abst_jp_ls
    #下記データ３つしか入っていない。要修正
    papercontents = [PaperContent(url,title_en,abst_en[i],title_jp,abst_jp[i],
        prob,sol,app,datetime.now().replace(microsecond=0),prob_est, sol_est, app_est) for i in range(len(abst_en))]#内包表記で一つづつPaperContent作成
    db_session.add_all(papercontents)
    db_session.commit()
    return redirect(url_for("index"))

@app.route("/update",methods=["post"])
def update():
    try:
        prob_con = PaperContent.query.filter_by(id=request.form.get("prob")).first()
        prob_con.prob = 1#probのDB更新
        db_session.add(prob_con)
    except AttributeError:
        pass

    try:
        sol_con = PaperContent.query.filter_by(id=request.form.get("sol")).first()
        sol_con.sol = 1#solのDB更新
        db_session.add(sol_con)
    except AttributeError:
        pass

    try:
        app_con = PaperContent.query.filter_by(id=request.form.get("app")).first()
        app_con.app = 1#appのDB更新
        db_session.add(app_con)
    except AttributeError:
        pass

    db_session.commit()

    return redirect(url_for("index"))
@app.route("/learn",methods=["post"])
def learn():
    #全データをDBから吸い出し
    all_data = db_session.query(PaperContent.abst_en, PaperContent.prob, PaperContent.sol, PaperContent.app).all()
    #ML.pyのlearning関数へ引き渡し、前処理、学習、モデルの保存
    model_score = learning(all_data)
    print("モデルの各カテゴリの精度は"+str(model_score)+"です。")

    #
    #

    return redirect(url_for("index"))

@app.route("/estimate",methods=["post"])
def estimate():
    #学習モデル読み込み
    #index.htmlの推定値更新(prob_est, sol_est, app_est)
    return redirect(url_for("index"))

@app.route("/delete",methods=["post"])
def delete():
    id_list = request.form.getlist("delete")
    for id in id_list:
        content = PaperContent.query.filter_by(id=id).first()
        db_session.delete(content)
    db_session.commit()
    return redirect(url_for("index"))

@app.route("/login",methods=["post"])
def login():
    user_name = request.form["user_name"]
    user = User.query.filter_by(user_name=user_name).first()
    if user:
        password = request.form["password"]
        hashed_password = sha256((user_name + password + key.SALT).encode("utf-8")).hexdigest()
        if user.hashed_password == hashed_password:
            session["user_name"] = user_name
            return redirect(url_for("index"))
        else:
            return redirect(url_for("top",status="wrong_password"))
    else:
        return redirect(url_for("top",status="user_notfound"))

@app.route("/logout")
def logout():
    session.pop("user_name", None)
    return redirect(url_for("top",status="logout"))

@app.route("/registar",methods=["post"])
def registar():
    user_name = request.form["user_name"]
    user = User.query.filter_by(user_name=user_name).first()
    if user:
        return redirect(url_for("newcomer",status="exist_user"))
    else:
        password = request.form["password"]
        hashed_password = sha256((user_name + password + key.SALT).encode("utf-8")).hexdigest()
        user = User(user_name, hashed_password)
        db_session.add(user)
        db_session.commit()
        session["user_name"] = user_name
        return redirect(url_for("index"))

@app.route("/top")
def top():
    status = request.args.get("status")
    return render_template("top.html",status=status)


@app.route("/newcomer")
def newcomer():
    status = request.args.get("status")
    return render_template("newcomer.html",status=status)

#app.pyをターミナルから直接呼び出した時だけ、app.run()を実行する
if __name__ == "__main__":
    app.run(debug=True)