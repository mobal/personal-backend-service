import logging
import sys

from argparse import ArgumentParser
from os.path import exists
from xml.etree import ElementTree

logging.basicConfig(format='%(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

parser = ArgumentParser(description='Fix source paths in generated coverage XML file')
parser.add_argument('-c', '--coverage-file', required=True, type=str, help='path of the coverage file')
parser.add_argument('-f', '--find', required=True, type=str, help='path to find for replace')
parser.add_argument('-r', '--replace', required=True, type=str, help='path to replace')

def _load_coverage(path: str) -> ElementTree:
    with open(path, 'r') as f:
        return ElementTree.parse(f)


def _replace_source(
        et: ElementTree,
        old_source: str,
        new_source: str) -> ElementTree:
    for el in et.iter('source'):
        el.text = el.text.replace(old_source, new_source)
    return et


def _save(et: ElementTree, path: str):
    with open(path, 'wb') as f:
        et.write(f, encoding='utf-8')


def main(cov_file: str, from_source: str, to_source: str):
    if exists(cov_file) is False:
        logger.error(f'File {cov_file} is not exists')
        sys.exit(-2)
    logger.info(f'Loading cov_file={cov_file}')
    et = _load_coverage(cov_file)
    logger.info(
        f'Replaces source values from old_source{from_source} to new_source={to_source}')
    et = _replace_source(et, old_source=from_source, new_source=to_source)
    logger.info(f'Save cov_file={cov_file}')
    _save(et, cov_file)


if __name__ == '__main__':
    args = parser.parse_args()
    main(args.coverage_file, args.find, args.replace)
