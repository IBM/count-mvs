"""
Copyright 2022 IBM Corporation All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""
# pylint: disable=global-statement,global-variable-not-assigned,invalid-name

from flask import Flask, Response, jsonify, request

app = Flask(__name__)

DEFAULT_ROUTE_CONFIGS = {
    "start_search": {"status_code": 201}, "results": {"status_code": 200}, "status": {"status_code": 200},
    "about": {"status_code": 200}
}
DEFAULT_SEARCHES = []
DEFAULT_SEARCH_DATA = []

route_configs = DEFAULT_ROUTE_CONFIGS.copy()
searches = DEFAULT_SEARCHES.copy()
search_data = DEFAULT_SEARCH_DATA.copy()


# Configuration endpoints
@app.route("/conf/route_configs/<endpoint>", methods=["POST"])
def set_route_config(endpoint):
    global route_configs
    route_configs[endpoint] = request.json
    return ""


@app.route("/conf/add_search_data", methods=["POST"])
def add_search_data():
    global search_data
    search_data = search_data + request.json
    return ""


@app.route("/conf/reset", methods=["POST"])
def reset():
    global route_configs
    global searches
    global search_data
    route_configs = DEFAULT_ROUTE_CONFIGS.copy()
    searches = DEFAULT_SEARCHES.copy()
    search_data = DEFAULT_SEARCH_DATA.copy()
    return ""


# Mock endpoints
@app.route("/api/ariel/searches", methods=["POST"])
def start_search():
    global route_configs
    global searches
    global search_data
    conf = route_configs["start_search"]
    if conf["status_code"] != 201:
        if conf["result"] is None:
            return Response("Failure!", status=conf["status_code"])
        else:
            return Response(conf["result"], status=conf["status_code"])

    search_id = 0
    for search in searches:
        if search["id"] >= search_id:
            search_id = search["id"] + 1
    data = {}
    if len(search_data) >= 1:
        data = search_data.pop(0)
    search = {"id": search_id, "data": data}
    searches.append(search)

    print(searches)

    return jsonify({"search_id": search_id}), 201


@app.route("/api/ariel/searches/<int:search_id>", methods=["GET"])
def get_status(search_id):
    global route_configs
    global searches
    conf = route_configs["status"]
    if conf["status_code"] != 200:
        return Response("Failure!", status=conf["status_code"])

    print(searches)

    for search in searches:
        if search["id"] == search_id:
            return jsonify(
                {"search_id": search_id, "record_count": 5, "completed": True, "progress": 100, "status": "COMPLETED"})

    return Response(f"No search found with id {search_id}", status=404)


@app.route("/api/ariel/searches/<int:search_id>/results", methods=["GET"])
def get_results(search_id):
    global route_configs
    global searches
    conf = route_configs["results"]
    if conf["status_code"] != 200:
        return Response("Failure!", status=conf["status_code"])

    for search in searches:
        if search["id"] == search_id:
            return jsonify(search["data"])

    return Response(f"No search found with id {search_id}", status=404)


@app.route("/api/system/about", methods=["GET"])
def get_about():
    global route_configs
    conf = route_configs["about"]
    if conf["status_code"] != 200:
        return Response("Failure!", status=conf["status_code"])
    return jsonify({"external_version": "7.5.0"})


if __name__ == "__main__":
    context = ("server.cert", "server.key")
    app.run(debug=True, ssl_context=context, host='0.0.0.0', port=443, threaded=False)
