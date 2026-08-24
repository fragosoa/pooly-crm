import random
import string

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

import db
from auth import admin_required

prospects_bp = Blueprint("prospects", __name__)


def _gen_id():
    # mirrors the frontend's uid(): Math.random().toString(36).slice(2, 10)
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choices(alphabet, k=8))


@prospects_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    # Deliberately just jwt_required (not admin_required): lets the frontend
    # tell "bad credentials" apart from "valid login, not an admin" so it can
    # show the right message instead of a generic 403 on login.
    username = get_jwt_identity()
    return jsonify({"username": username, "is_admin": db.is_user_admin(username)})


@prospects_bp.route("/prospects", methods=["GET"])
@admin_required
def list_prospects():
    return jsonify({"prospects": db.list_prospects()})


@prospects_bp.route("/prospects/<prospect_id>", methods=["GET"])
@admin_required
def get_prospect(prospect_id):
    p = db.get_prospect(prospect_id)
    if p is None:
        return jsonify({"msg": "Not found"}), 404
    return jsonify(p)


@prospects_bp.route("/prospects", methods=["POST"])
@admin_required
def create_prospect():
    data = request.get_json() or {}
    if not data.get("empresa"):
        return jsonify({"msg": "empresa is required"}), 400
    prospect_id = data.get("id") or _gen_id()
    p = db.create_prospect(prospect_id, data)
    return jsonify(p), 201


@prospects_bp.route("/prospects/<prospect_id>", methods=["PUT", "PATCH"])
@admin_required
def update_prospect(prospect_id):
    data = request.get_json() or {}
    if db.get_prospect(prospect_id) is None:
        return jsonify({"msg": "Not found"}), 404
    p = db.update_prospect(prospect_id, data)
    return jsonify(p)


@prospects_bp.route("/prospects/<prospect_id>", methods=["DELETE"])
@admin_required
def delete_prospect(prospect_id):
    ok = db.delete_prospect(prospect_id)
    if not ok:
        return jsonify({"msg": "Not found"}), 404
    return jsonify({"msg": "deleted"}), 200


@prospects_bp.route("/prospects/bulk", methods=["POST"])
@admin_required
def bulk_upsert():
    data = request.get_json() or {}
    prospects = data.get("prospects", [])
    for p in prospects:
        if not p.get("id"):
            p["id"] = _gen_id()
    count = db.upsert_many(prospects)
    return jsonify({"upserted": count}), 200
