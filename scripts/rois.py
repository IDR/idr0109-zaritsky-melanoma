#!/usr/bin/env python

import os
import re
import omero
from omero.gateway import BlitzGateway
from omero.rtypes import (
    rdouble,
    rint,
    rstring
)

DATASET_ID = 13801
DELETE_ROIS = True
DRYRUN = False
W = 256
H = 256

# Generated with:
# /uod/idr/filesets/idr0109-zaritsky-melanoma/20210408-ftp/ROI>
# find * -type f -name "*.png" >> /tmp/rois.txt
roipaths = "/tmp/rois.txt"


def delete_rois(conn):
    for img in conn.getObjects('Image', opts={'dataset': DATASET_ID}):
        result = conn.getRoiService().findByImage(img.id, None)
        to_delete = []
        for roi in result.rois:
            for s in roi.copyShapes():
                if type(s) == omero.model.RectangleI:
                    to_delete.append(roi.getId().getValue())
                    break
        if to_delete:
            print(f"Deleting existing {len(to_delete)} rois on image {img.name}.")
            conn.deleteObjects("Roi", to_delete, deleteChildren=True, wait=True)


def create_roi(img, x, y, t, text=None):
    roi = omero.model.RoiI()
    roi.setImage(img._obj)
    rect = omero.model.RectangleI()
    rect.x = rdouble(x)
    rect.y = rdouble(y)
    rect.width = rdouble(W)
    rect.height = rdouble(H)
    if text:
        rect.textValue = rstring(text)
    rect.theZ = rint(0)
    rect.theT = rint(t)
    roi.addShape(rect)
    return roi


def main(conn):
    #example file name:
    # /uod/idr/filesets/idr0109-zaritsky-melanoma/20210408-ftp/ROI/png/high/m405/150312_m405_m610/150312_m405_s01_t171_x946_y946_t309/150312_m405_s01_t171_x946_y946_t309_t7Ready_f00001.png
    FORMAT = "png/(.+)/(.+)/(.+)/.+/(.+)"
    #             high/low      xyz
    #                  celltype     roi_info
    #                      img_name

    #150312_m405_s01_t171_x946_y946_t309_t7Ready_f00001.png
    ROI_FORMAT = ".*_s(\d\d)_t(\d+)_x(\d+)_y(\d+)_t(\d+)_.+f(\d+)"

    if not DRYRUN and DELETE_ROIS:
        delete_rois(conn)

    i = 0
    c = 0
    entries = open(roipaths, 'r').readlines()
    for entry in entries:
        entry = entry.strip()
        i += 1
        fmatch = re.search(FORMAT, entry, re.IGNORECASE)
        if fmatch:
            high_low = fmatch.group(1)
            cell_type = fmatch.group(2)
            img_name = fmatch.group(3)
            roi_info = fmatch.group(4)
            rmatch = re.search(ROI_FORMAT, roi_info, re.IGNORECASE)
            if rmatch:
                s = rmatch.group(1)
                # 150309_m610_m405.nd2 [150309_m610_m405.nd2 (series 01)]
                img_name = f"{img_name}.nd2 [{img_name}.nd2 (series {s})]"
                if not "150414_m116" in img_name: # testing: just do one image for now
                    print(f"({i}/1706003)")
                    continue
                t_from = int(rmatch.group(2))
                x = int(rmatch.group(3))
                y = int(rmatch.group(4))
                # x,y seems to be the center of the ROI
                x -= W/2
                y -= H/2
                t_to = int(rmatch.group(5))
                t_inc = int(rmatch.group(6))
                t = t_from + t_inc
                if t > t_to:
                    print(f"Unexpected t={t}! t_from={t_to} t_to={t_to} t_inc={t_inc}\nline: {entry}")
                try:
                    img = conn.getObject('Image', opts={'dataset': DATASET_ID}, attributes={"name": img_name})
                    roi = create_roi(img, x, y, t, f"{cell_type}, {high_low}")
                    if not DRYRUN:
                        try:
                            roi = conn.getUpdateService().saveAndReturnObject(roi, conn.SERVICE_OPTS)
                            print(f"Saved ROI ({roi.getId().getValue()}) for image {img_name}")
                            c += 1
                        except:
                            print(f"Saving ROI for image {img_name} failed!")
                    else:
                        print(f"Created ROI for image {img_name} (dry run)")
                except:
                    print(f"Image {img_name} not found!")
            else:
                "Unexpected format\nline: {entry}"
        else:
                "Unexpected format\nline: {entry}"
        print(f"({i}/1706003)")
    print(f"Created {c} ROIs")

if __name__ == '__main__':
    host = os.environ.get('OMERO_HOST', 'localhost')
    port = os.environ.get('OMERO_PORT', '4064')
    user = os.environ.get('OMERO_USER', 'NA')
    pw = os.environ.get('OMERO_PASSWORD', 'NA')
    with BlitzGateway(user, pw, host=host, port=port) as conn:
        main(conn)
