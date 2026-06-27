import os
from dotenv import load_dotenv

env = os.environ.get("FLASK_ENV", "prd")
env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), f".env.{env}")
load_dotenv(env_file)

from flask import Flask, jsonify, request
from flask_restful import Api
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from flask_swagger_ui import get_swaggerui_blueprint
from blacklist import BLACKLIST

import appController
import config.env as memory


app = Flask(__name__)
app.config["PROPAGATE_EXCEPTIONS"] = True
app.config["JWT_SECRET_KEY"] = memory.jwt["JWT_SECRET_KEY"]
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = memory.jwt["JWT_ACCESS_TOKEN_EXPIRES"]
app.config["JWT_BLACKLIST_ENABLED"] = True

jwt = JWTManager(app)  

@jwt.token_in_blacklist_loader
def verifica_blacklist(token):
    return token['jti'] in BLACKLIST

@jwt.revoked_token_loader
def token_de_acesso_invalidado():
    return jsonify({"msg": 'Token expirado!'}), 401

@jwt.invalid_token_loader
def token_invalido(callback):
    return jsonify({"msg": 'Token inválido ou ausente. Verifique o cabeçalho Authorization.'}), 401

### swagger config ###
SWAGGER_URL = '/swagger'
API_URL = memory.utilits["HOST"]+'/static/swagger.json'
SWAGGERUI_BLUEPRINT = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        "app_name": 'Seans-Python-Flask-REST-Boilerplate'
    }
)

app.register_blueprint(SWAGGERUI_BLUEPRINT, url_prefix=SWAGGER_URL)

@app.after_request
def add_no_cache(response):
    if request.path.startswith('/static/swagger'):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

api = Api(app)

#Version
api.add_resource(appController.VersionController, '/version')

#Metatrader Login
api.add_resource(appController.MetatraderLoginController, '/metatrader/login')

#Metatrader Trade Start
api.add_resource(appController.MetatraderTradeStartController, '/metatrader/trade/start')

#Metatrader Trade Exit
api.add_resource(appController.MetatraderTradeExitController, '/metatrader/trade/exit')

#Metatrader Data (candles)
api.add_resource(appController.MetatraderDataController, '/metatrader/data')

#Metatrader Log (debug)
api.add_resource(appController.Mt5LogController, '/metatrader/log')

#Claude Trader (entrega de ordens pro MT5 — consumer da guia gerada no iavest-backend)
api.add_resource(appController.ClaudeTraderOrdemController, '/claude-trader/ordem')

#touch ~/apps_wsgi/stg.wsgi


if __name__ == '__main__':
    app.run(debug=True)