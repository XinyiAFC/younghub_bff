from flask import Blueprint, jsonify, request
from app.util.azure_cosmos_util import AzureCosmosUtil

card_bp = Blueprint('cards', __name__)

_cosmos = AzureCosmosUtil()

@card_bp.route('/articles')
def get_card():
    # During ID Schema v2 migration, channel=101/102/103 reads both the new
    # and legacy partition, with the new partition winning for duplicate ids.
    channel = request.args.get("channel")
    top = request.args.get("top", type=int)   # 可选：限制返回条数
    items = _cosmos.read_article_list(channel_id=channel, top=top)
    resp = jsonify(items)
    resp.headers["Cache-Control"] = "no-store"
    return resp, 200


@card_bp.route('/events')
def get_events():
    top = request.args.get("top", type=int)
    resp = jsonify(_cosmos.read_event_list(top=top))
    resp.headers["Cache-Control"] = "no-store"
    return resp, 200


@card_bp.route('/services')
def get_services():
    top = request.args.get("top", type=int)
    resp = jsonify(_cosmos.read_service_list(top=top))
    resp.headers["Cache-Control"] = "no-store"
    return resp, 200
