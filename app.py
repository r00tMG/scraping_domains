import csv

from flasgger import Swagger
from flask import Flask, jsonify
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


def get_pending_domains_from_expired_domain_flask():
    def read_pending_domains_from_expired_domain_csv():
        with open('pending_domains_from_expired_domains.csv', mode='r') as file:
            csv_reader = csv.DictReader(file)
            return [row for row in csv_reader]

    @app.route('/get_pending_domains_from_expired_domains', methods=['GET'])
    def get_items_pending_domains_from_expired_domains():
        """
                Get pending domains from expired domains CSV file
                ---
                responses:
                  200:
                    description: List of pending domains from the pending_delete1 CSV file
                """
        items = read_pending_domains_from_expired_domain_csv()
        return jsonify(items)


def get_pending_domains_flask():
    def read_pending_domains_from_checkpagerank_csv():
        with open('domain_pending.csv', mode='r') as file:
            csv_reader = csv.DictReader(file)
            return [row for row in csv_reader]

    @app.route('/get_pending_domains', methods=['GET'])
    def get_items_pending_domains():
        """
                Get pending domains from expired domains CSV file
                ---
                responses:
                  200:
                    description: List of pending domains from the pending_delete1 CSV file
                """
        items = read_pending_domains_from_checkpagerank_csv()
        return jsonify(items)


def get_deleted_domains_from_expired_domain_flask():
    def read_deleted_domains_from_expired_domain_csv():
        with open('deleted_domains_from_expired_domains.csv', mode='r') as file:
            csv_reader = csv.DictReader(file)
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
