"""Validate workflow YAML, rejecting duplicate keys rather than hiding them."""
from pathlib import Path
import yaml


class UniqueLoader(yaml.BaseLoader):
    pass


def unique_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in result:
            raise ValueError(f'duplicate YAML key: {key}')
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def main():
    files = sorted(Path('.github/workflows').glob('*.yml')) + sorted(Path('.github/workflows').glob('*.yaml'))
    if not files:
        raise SystemExit('No workflow files found')
    for path in files:
        document = yaml.load(path.read_text(encoding='utf-8'), Loader=UniqueLoader)
        if not isinstance(document, dict) or not document.get('on') or not document.get('jobs'):
            raise ValueError(f'{path}: workflow needs on and jobs')
        for name, job in document['jobs'].items():
            if not isinstance(job, dict) or not ('runs-on' in job or 'uses' in job):
                raise ValueError(f'{path}: invalid job {name}')
    print(f'Validated {len(files)} workflows (unique keys, events and jobs)')


if __name__ == '__main__':
    main()
