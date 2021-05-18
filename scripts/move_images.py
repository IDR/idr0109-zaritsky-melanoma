import csv
import omero.cli
import omero.gateway

"""
Move images into correct dataset
"""

ANNO_FILE = "/uod/idr/metadata/idr0109-zaritsky-melanoma/experimentA/idr0109-experimentA-annotation.csv"
PROJECT_ID = 1803


def get_images(project):
    for dataset in project.listChildren():
        for image in dataset.listChildren():
            yield (dataset, image)


def unlink_dataset(conn, image):
    params = omero.sys.ParametersI()
    params.add('id', omero.rtypes.rlong(image.getId()))
    query = "select l from DatasetImageLink as l where l.child.id=:id"
    query_service = conn.getQueryService()
    link = query_service.findAllByQuery(query, params, conn.SERVICE_OPTS)
    links_ids = [link[0].getId().getValue()]
    conn.deleteObjects('DatasetImageLink', links_ids, wait=True)
    print(f"Unlinked {image.getName()}")


def link_dataset(conn, dataset, image):
    link = omero.model.DatasetImageLinkI()
    link.setParent(omero.model.DatasetI(dataset.getId(), False))
    link.setChild(omero.model.ImageI(image.getId(), False))
    conn.getUpdateService().saveObject(link)
    print(f"Linked {image.getName()}")


def create_dataset(conn, project, dataset_name):
    dataset = omero.model.DatasetI()
    dataset.setName(omero.rtypes.rstring(dataset_name))
    dataset = conn.getUpdateService().saveAndReturnObject(dataset)
    dataset_id = dataset.getId().getValue()
    link = omero.model.ProjectDatasetLinkI()
    link.setParent(omero.model.ProjectI(project.getId(), False))
    link.setChild(omero.model.DatasetI(dataset.getId(), False))
    conn.getUpdateService().saveObject(link)
    return dataset


if __name__ == "__main__":
    dataset_map = {}
    with open(ANNO_FILE, newline='') as file:
        reader = csv.reader(file, delimiter=',')
        for row in reader:
            dataset_map[row[1]] = row[0]
            print(f"{row[1]} -> {row[0]}")

    with omero.cli.cli_login() as c:
        conn = omero.gateway.BlitzGateway(client_obj=c.get_client())
        project = conn.getObject("Project", attributes={'id': PROJECT_ID})

        for dataset, image in get_images(project):
            if image.getName() in dataset_map:
                tgt_dataset_name = dataset_map[image.getName()]
                if tgt_dataset_name != dataset.getName():
                    tgt = None
                    try:
                        tgt = conn.getObject("Dataset", attributes={'name': tgt_dataset_name})
                    except:
                        print(f"Dataset {tgt_dataset_name} not found, trying to create it.")
                    if not tgt:
                        try:
                            tgt = create_dataset(conn, project, tgt_dataset_name)
                        except:
                            print(f"Can't create dataset {tgt_dataset_name} !")
                            continue
                    unlink_dataset(conn, image)
                    link_dataset(conn, tgt, image)
            else:
                print(f"Image {image.getName()} not found in {ANNO_FILE} !")
