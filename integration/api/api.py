from flask import Flask, Response, jsonify, request

app = Flask(__name__)

DEFAULT_ROOT_CONFIGS = {
    "start_search": {
        "status_code": 200
    },
    "results": {
        "status_code": 200
    },
    "status": {
        "status_code": 200
    }
}
DEFAULT_SEARCHES = []
DEFAULT_SEARCH_DATA = []

route_configs = DEFAULT_ROOT_CONFIGS.copy()
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
    route_configs = DEFAULT_ROOT_CONFIGS.copy()
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
    if not conf["status_code"] == 200:
        return Response("Failure!", status=conf["status_code"])

    id = 0
    for search in searches:
        if search["id"] >= id:
            id = search["id"] + 1
    data = {}
    if len(search_data) >= 1:
        data = search_data.pop(0)
    search = {"id": id, "data": data}
    searches.append(search)

    print(searches)

    return jsonify({"search_id": id})


@app.route("/api/ariel/searches/<int:id>", methods=["GET"])
def get_status(id):
    global route_configs
    global searches
    conf = route_configs["status"]
    if not conf["status_code"] == 200:
        return Response("Failure!", status=conf["status_code"])

    print(searches)

    for search in searches:
        if search["id"] == id:
            return jsonify({"status": "COMPLETED"})

    return Response(f"No search found with id {id}", status=404)


@app.route("/api/ariel/searches/<int:id>/results", methods=["GET"])
def get_results(id):
    global route_configs
    global searches
    conf = route_configs["results"]
    if not conf["status_code"] == 200:
        return Response("Failure!", status=conf["status_code"])

    for search in searches:
        if search["id"] == id:
            return jsonify(search["data"])

    return Response(f"No search found with id {id}", status=404)


if __name__ == "__main__":
    context = ("server.cert", "server.key")
    app.run(debug=True,
            ssl_context=context,
            host='0.0.0.0',
            port=443,
            threaded=False)
