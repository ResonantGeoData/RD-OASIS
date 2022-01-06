from pathlib import Path

import pytest
from rgd.models import ChecksumFile


@pytest.mark.django_db(transaction=True)
def test_rest_dataset_update_files(dataset, checksum_file_factory, authenticated_api_client):
    new_file = checksum_file_factory()

    file_ids = [f.id for f in dataset.files.all()]
    files_to_remove = file_ids[:2]

    r = authenticated_api_client.put(
        f'/api/datasets/{dataset.id}/files/',
        {
            'insert': [new_file.id],
            'delete': files_to_remove,
        },
        format='json',
    )

    assert r.status_code == 200
    assert new_file.id in r.json()['files']
    assert not set(files_to_remove) & set(r.json()['files'])


@pytest.mark.django_db(transaction=True)
def test_rest_dataset_update_files_invalid(dataset, authenticated_api_client):
    """Try to insert file that doesn't exist."""
    invalid_file_id = -1
    r = authenticated_api_client.put(
        f'/api/datasets/{dataset.id}/files/',
        {
            'insert': [invalid_file_id],
            'delete': [],
        },
        format='json',
    )

    assert r.status_code == 400
    assert type(r.json()['insert']) == str
    assert invalid_file_id not in [f.id for f in dataset.files.all()]


@pytest.mark.django_db(transaction=True)
def test_rest_dataset_tree(dataset, checksum_file_factory, admin_api_client):
    """Test that the tree list endpoint functions as expected."""
    # Top level
    file1: ChecksumFile = checksum_file_factory(name='h.txt')

    # a/ directory
    file2: ChecksumFile = checksum_file_factory(name='a/f.txt')
    file3: ChecksumFile = checksum_file_factory(name='a/g.txt')

    # a/b/ directory
    file4: ChecksumFile = checksum_file_factory(name='a/b/d.txt')
    file5: ChecksumFile = checksum_file_factory(name='a/b/e.txt')
    file6: ChecksumFile = checksum_file_factory(name='a/b/c.jpg')

    dataset.files.set([file1, file2, file3, file4, file5, file6])

    # Testing folders
    folder_b = [file4, file5, file6]
    folder_a = [file2, file3] + folder_b

    known_size_a = sum([f.size for f in folder_a if f.size is not None])
    a_created = min([file.created for file in folder_a]).isoformat()
    a_modified = max([file.modified for file in folder_a]).isoformat()

    known_size_b = sum([f.size for f in folder_b if f.size is not None])
    b_created = min([file.created for file in folder_b]).isoformat()
    b_modified = max([file.modified for file in folder_b]).isoformat()

    # Check top level response
    r = admin_api_client.get(f'/api/datasets/{dataset.id}/tree/')
    assert r.json()['files'][file1.name]['id'] == file1.id
    assert r.json()['folders'] == {
        'a': {
            'known_size': known_size_a,
            'num_files': len(folder_a),
            'num_url_files': 1,
            'created': a_created,
            'modified': a_modified,
        }
    }

    # Search folder 'a'
    r = admin_api_client.get(f'/api/datasets/{dataset.id}/tree/', {'path_prefix': 'a'})

    # Files
    files = r.json()['files']
    assert files[Path(file2.name).name]['id'] == file2.id
    assert files[Path(file3.name).name]['id'] == file3.id

    # Folders
    assert r.json()['folders'] == {
        'b': {
            'known_size': known_size_b,
            'num_files': len(folder_b),
            'num_url_files': 1,
            'created': b_created,
            'modified': b_modified,
        }
    }

    # Search folder 'a/b'
    r = admin_api_client.get(f'/api/datasets/{dataset.id}/tree/', {'path_prefix': 'a/b'})

    # Files
    files = r.json()['files']
    assert files[Path(file4.name).name]['id'] == file4.id
    assert files[Path(file5.name).name]['id'] == file5.id
    assert files[Path(file6.name).name]['id'] == file6.id
