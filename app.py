import csv

from flask import Flask, jsonify


def get_domains_from_robot_flask():
    def read_domains_from_robot_csv():
        with open('domains_from_robot.csv', mode='r') as file:
            csv_reader = csv.DictReader(file)
            return [row for row in csv_reader]

    @app.route('/get_domains_from_robot', methods=['GET'])
    def get_items():
        items = read_domains_from_robot_csv()
        return jsonify(items)


def get_pending_domains_from_expired_domain_flask():
    def read_pending_domains_csv():
        with open('domains.csv', mode='r') as file:
            csv_reader = csv.DictReader(file)
            return [row for row in csv_reader]

    @app.route('/get_domains_from_expired_domains', methods=['GET'])
    def get_items_pending_domains_from_expired_domains():
        items = read_pending_domains_csv()
        return jsonify(items)


def get_deleted_domains_from_expired_domain_flask():
    def read_deleted_domains_csv():
        with open('deleted_domains.csv', mode='r') as file:
            csv_reader = csv.DictReader(file)
            return [row for row in csv_reader]

    @app.route('/get_deleted_domains_from_expired_domains', methods=['GET'])
    def get_items_deleted_domains_from_expired_domains():
        items = read_deleted_domains_csv()
        return jsonify(items)


def get_domains_from_godaddy_flask():
    def read_domains_godaddy_csv():
        with open('domain_godaddy.csv', mode='r') as file:
            csv_reader = csv.DictReader(file)
            return [row for row in csv_reader]

    @app.route('/get_domains_from_godaddy', methods=['GET'])
    def get_items_domains_from_godaddy():
        items = read_domains_godaddy_csv()
        return jsonify(items)


app = Flask(__name__)

get_domains_from_robot_flask()
get_pending_domains_from_expired_domain_flask()
get_deleted_domains_from_expired_domain_flask()
get_domains_from_godaddy_flask()

if __name__ == '__main__':
    app.run(debug=True)