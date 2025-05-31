from flask import  Blueprint, request, g

from app.services.auth.auth_service import register_user, login_user, get_user_info
from app.utils.tokenUtils import token_required

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=['POST'])
async def register():
    data = request.get_json()
    return register_user(data)

@bp.route('/login', methods=['POST'])
async def login():
    data = request.get_json()
    return login_user(data)

@bp.route('/info', methods=['GET'])
@token_required
async def user_info():
    user = g.user
    return get_user_info(user)