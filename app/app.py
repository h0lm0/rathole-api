from flask import Flask, request, jsonify
from flask_basicauth import BasicAuth
import os
import toml

app = Flask(__name__)

# Configuration de l'authentification Basic
app.config['BASIC_AUTH_USERNAME'] = os.getenv('RAT_API_USERNAME')
app.config['BASIC_AUTH_PASSWORD'] = os.getenv('RAT_API_PASSWORD')

RAT_FILE = os.getenv("RAT_FILE_PATH")  # Default path if not set

basic_auth = BasicAuth(app)

@app.route("/start_tunnel", methods=["POST"])
@basic_auth.required
def start_tunnel():
    # verif json
    data = request.get_json()
    if not data or "container_id" not in data or "container_port" not in data or "public_port" not in data:
        return jsonify({"error": "Données manquantes. Les champs 'container_id', 'container_port' et 'public_port' sont requis."}), 400

    container_id = data["container_id"]
    container_port = data["container_port"]
    public_port = data["public_port"]

    try:
        container_port = int(container_port)
        public_port = int(public_port)
        if not (1 <= container_port <= 65535) or not (1 <= public_port <= 65535):
            return jsonify({"error": "Les ports doivent être compris entre 1 et 65535."}), 400
    except ValueError:
        return jsonify({"error": "Les ports doivent être des nombres entiers."}), 400

    try:
        config = toml.load(RAT_FILE) if os.path.exists(RAT_FILE) else {"client": {"services": {}}}
    except toml.TomlDecodeError as e:
        return jsonify({"error": f"Erreur lors de la lecture du fichier de configuration : {e}"}), 500

    config["client"]["services"][container_id] = {
        "type": "tcp",
        "local_addr": f"0.0.0.0:{container_port}"
    }

    # Écriture dans le fichier
    try:
        with open(RAT_FILE, "w") as f:
            toml.dump(config, f)
    except IOError as e:
        return jsonify({"error": f"Erreur lors de l'écriture dans le fichier de configuration : {e}"}), 500

    return jsonify({"status": "Tunnel started"}), 200

@app.route("/stop_tunnel", methods=["POST"])
@basic_auth.required
def stop_tunnel():
    data = request.get_json()
    if not data or "container_id" not in data:
        return jsonify({"error": "Données manquantes. Le champ 'container_id' est requis."}), 400

    container_id = data["container_id"]

    try:
        config = toml.load(RAT_FILE)
    except FileNotFoundError:
        return jsonify({"error": "Le fichier de configuration n'existe pas."}), 404
    except toml.TomlDecodeError as e:
        return jsonify({"error": f"Erreur lors de la lecture du fichier de configuration : {e}"}), 500

    if "services" in config["client"] and container_id in config["client"]["services"]:
        del config["client"]["services"][container_id]

        try:
            with open(RAT_FILE, "w") as f:
                toml.dump(config, f)
        except IOError as e:
            return jsonify({"error": f"Erreur lors de la modification du fichier de configuration : {e}"}), 500

        return jsonify({"status": "Tunnel stopped"}), 200
    else:
        return jsonify({"error": "Aucun tunnel trouvé avec ce nom."}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
