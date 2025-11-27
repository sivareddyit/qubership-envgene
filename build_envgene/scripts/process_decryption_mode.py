import argparse
import os

from envgenehelper import crypt


def process_decryption_mode(cred_path):
    crypt.decrypt_file(cred_path, ignore_is_crypt=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--env_name', help="", type=str)
    args = parser.parse_args()

    base_dir = os.getenv("CI_PROJECT_DIR")
    cluster_name = args.env_name.split('/')[0].strip()
    cred_path = os.path.join(base_dir, 'environments', cluster_name, 'cloud-passport', cluster_name + '-creds.yml')
    config_path = os.path.join(base_dir, 'configuration/config.yml')

    process_decryption_mode(cred_path)
