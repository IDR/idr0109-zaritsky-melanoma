import logging
import omero.cli
import omero.gateway


DESC = """
Sets the channel names
"""

CONTAINER_TYPE = "Project"
CONTAINER_ID = 1751
CHANNEL_NAMES = ["Cells"]

def get_images(container):
    if isinstance(container, omero.gateway.DatasetWrapper):
        for image in container.listChildren():
            yield image
    elif isinstance(container, omero.gateway.ProjectWrapper):
        for dataset in container.listChildren():
            for image in dataset.listChildren():
                yield image
    elif isinstance(container, omero.gateway.PlateWrapper):
        for well in container.listChildren():
            index = well.countWellSample()
            for index in range(0, index):
                yield well.getImage(index)
    elif isinstance(container, omero.gateway.ScreenWrapper):
        for plate in container.listChildren():
            for well in plate.listChildren():
                index = well.countWellSample()
                for index in range(0, index):
                    yield well.getImage(index)


def set_channel_names(image, channel_names):
    channels = image.getChannels(noRE=True)
    if len(channels) != len(channel_names):
        log.warn(f"Number of channels doesn't match number\
            of channel names. Ignoring image {image.getName()}")
        return False
    for i in range(0, len(channel_names)):
        lc = channels[i].getLogicalChannel()
        lc.setName(channel_names[i])
        lc.save()
    return True


if __name__ == "__main__":
    with omero.cli.cli_login() as c:
        conn = omero.gateway.BlitzGateway(client_obj=c.get_client())
        container = conn.getObject(CONTAINER_TYPE, attributes={"id": CONTAINER_ID})
        images = get_images(container)
        for image in images:
            set_channel_names(image, CHANNEL_NAMES)
