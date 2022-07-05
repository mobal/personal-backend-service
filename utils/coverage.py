import logging
import sys

from argparse import ArgumentParser
from os.path import exists
from xml.etree import ElementTree

logging.basicConfig(format='%(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

parser = ArgumentParser(
    description='Fix source paths in generated coverage XML file')
parser.add_argument(
    '-c',
    '--coverage-file',
    required=True,
    type=str,
    help='path of the coverage file')
parser.add_argument(
    '-f',
    '--find',
    required=True,
    type=str,
    help='path to find for replace')
parser.add_argument(
    '-r',
    '--replace',
    required=True,
    type=str,
    help='path to replace')


def _load_coverage(path: str) -> ElementTree:
    with open(path, 'r') as f:
        return ElementTree.parse(f)


def _replace_source(
        et: ElementTree,
        find: str,
        replace: str) -> ElementTree:
    for el in et.iter('source'):
        el.text = el.text.replace(find, replace)
    return et


def _save(et: ElementTree, path: str):
    with open(path, 'wb') as f:
        et.write(f, encoding='utf-8')


def main(coverage_file: str, path_to_find: str, path_to_replace: str):
    if exists(coverage_file) is False:
        logger.error(f'File coverage_file={coverage_file} is not exists')
        sys.exit(-2)
    logger.info(f'Load coverage_file={coverage_file}')
    et = _load_coverage(coverage_file)
    logger.info(
        f'Find and replace source path_to_find={path_to_find} to path_to_replace={path_to_replace}')
    et = _replace_source(et, find=path_to_find, replace=path_to_replace)
    logger.info(f'Save cov_file={coverage_file}')
    _save(et, coverage_file)


if __name__ == '__main__':
    args = parser.parse_args()
    main(args.coverage_file, args.find, args.replace)
