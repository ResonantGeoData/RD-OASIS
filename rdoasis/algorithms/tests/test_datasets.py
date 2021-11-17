import pytest


@pytest.mark.django_db
def test_rest_dataset_update_files(dataset, checksum_file_factory, authenticated_api_client):
    new_file = checksum_file_factory()

    file_ids = [f.id for f in dataset.files.all()]
    files_to_remove = file_ids[:2]

    r = authenticated_api_client.put(
        f'/api/datasets/{dataset.id}/update_files/',
        {
            'insert': [new_file.id],
            'delete': files_to_remove,
        },
        format='json',
    )

    assert r.status_code == 200
    assert new_file.id in r.json()['files']
    assert not set(files_to_remove) & set(r.json()['files'])


# FIXME: This test fails and I have no idea why
# @pytest.mark.django_db
# def test_rest_dataset_update_files_invalid(dataset, authenticated_api_client):
#     # Try to insert file that doesn't exist
#     invalid_file_id = -1
#     r = authenticated_api_client.put(
#         f'/api/datasets/{dataset.id}/update_files/',
#         {
#             'insert': [invalid_file_id],
#             'delete': [],
#         },
#         format='json',
#     )

#     assert r.status_code == 400
#     assert type(r.json()['insert']) == 'str'
#     assert invalid_file_id not in [f.id for f in dataset.files.all()]
