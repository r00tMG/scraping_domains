import csv
import os
from venv import logger

from flasgger import Swagger
from flask import Flask, jsonify, request


#CORS(app)


# def get_domains_from_robot_flask():
#     def read_domains_from_robot_csv():
#         with open('domains_from_robot.csv', mode='r') as file:
#             csv_reader = csv.DictReader(file)
#             return [row for row in csv_reader]
#
#     @app.route('/get_domains_from_robot', methods=['GET'])
#     def get_items():
#         items = read_domains_from_robot_csv()
#         return jsonify(items)
def read_csv_file(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Le fichier {file_path} est introuvable.")
    if os.stat(file_path).st_size == 0:
        raise ValueError(f"Le fichier {file_path} est vide.")
    with open(file_path, mode='r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file, delimiter=',', restval=None)
        total_lines = sum(1 for _ in file)
        print("Nombre de lignes :", total_lines)
        file.seek(0)  # Réinitialiser le curseur au début du fichier
        for row in csv_reader:
            if any(cell.strip() for cell in row.values()):  # Exclure les lignes vides
                yield row
            else:
                logger.warning(f"Ligne vide ou malformée : {row}")


def paginate_data(data, page, per_page):
    start = (page - 1) * per_page
    end = page * per_page
    print(f"Paginating data: start={start}, end={end}, total={len(data)}")
    return data[start:end]


def get_pending_domains_from_expired_domain_flask():
    @app.route('/get_pending_domains_from_expired_domains', methods=['GET'])
    def get_items_pending_domains_from_expired_domains():
        """
                Get pending domains from expired domains CSV file
                ---
                responses:
                  200:
                    description: List of pending domains from the pending_delete1 CSV file
                """
        app.logger.debug("Request received for /health/get_pending_domains")
        try:
            # Fetch data
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 5000, type=int)
            # Lecture paresseuse et pagination des données
            data = list(read_csv_file('pending_domains_from_expired_domains.csv'))
            unique_rows = set(tuple(row) for row in data)
            print(f"Lignes uniques : {len(unique_rows)}")
            # Transformer en liste pour la pagination
            paginated_data = paginate_data(data, page, per_page)
            return jsonify({'status': 'success', 'size': len(paginated_data), 'data': paginated_data})
        except Exception as e:
            app.logger.error(f"Error: {e}")
            return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


def get_pending_domains_flask():

    @app.route('/get_pending_domains', methods=['GET'])
    def get_items_pending_domains():
        """
                Get pending domains from expired domains CSV file
                ---
                responses:
                  200:
                    description: List of pending domains from the pending_delete1 CSV file
                """
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 5000, type=int)
        # Lecture paresseuse et pagination des données
        data = list(read_csv_file('domain_pending.csv'))
        unique_rows = set(tuple(row) for row in data)
        print(f"Lignes uniques : {len(unique_rows)}")
        # Transformer en liste pour la pagination
        paginated_data = paginate_data(data, page, per_page)
        return jsonify(paginated_data)


def get_deleted_domains_from_expired_domain_flask():
    def read_deleted_domains_from_expired_domain_csv():
        with open('deleted_domains_from_expired_domains.csv', mode='r') as file:
            csv_reader = csv.reader(file)
            return [row for row in csv_reader]

    @app.route('/get_deleted_domains_from_expired_domains', methods=['GET'])
    def get_items_deleted_domains_from_expired_domains():
        """
                Get pending domains from expired domains CSV file
                ---
                responses:
                  200:
                    description: List of pending domains from the pending_delete1 CSV file
                """
        items = read_deleted_domains_from_expired_domain_csv()
        return jsonify(items)


def get_deleted_domains_flask():
    def read_delteted_domains_from_checkpagerank_csv():
        with open('domain_expired.csv', mode='r') as file:
            csv_reader = csv.DictReader(file)
            return [row for row in csv_reader]

    @app.route('/get_deleted_domains', methods=['GET'])
    def get_items_deleted_domains():
        """
                Get deleted domains from expired domains CSV file
                ---
                responses:
                  200:
                    description: List of deleted domains from the deleted_domains_expired_net1 CSV file
                """
        items = read_delteted_domains_from_checkpagerank_csv()
        return jsonify(items)


app = Flask(__name__)
swagger = Swagger(app)

get_pending_domains_from_expired_domain_flask()
get_pending_domains_flask()
get_deleted_domains_from_expired_domain_flask()
get_deleted_domains_flask()

if __name__ == '__main__':
    app.run(debug=True)
