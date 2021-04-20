#!/usr/bin/env python

import os
import re
import omero
from omero.gateway import BlitzGateway
from omero_rois import mask_from_binary_image
from skimage.io import imread

maskpaths = "/tmp/masks.txt"

DATASET_ID = 13801
DELETE_ROIS = True
DRYRUN = False
W = 256
H = 256


def delete_rois(conn):
  for img in conn.getObjects('Image', opts={'dataset': DATASET_ID}):
    result = conn.getRoiService().findByImage(img.id, None)
    to_delete = []
    for roi in result.rois:
      for s in roi.copyShapes():
        if type(s) == omero.model.MaskI:
          to_delete.append(roi.getId().getValue())
          break
    if to_delete:
      print(f"Deleting existing {len(to_delete)} masks on image {img.name}.")
      conn.deleteObjects("Roi", to_delete, deleteChildren=True, wait=True)


def create_mask(mask_path, x_offset, y_offset, t, text):
  try:
    mask = mask_from_binary_image(imread(mask_path), rgba=(255, 255, 255, 128),
                                  t=t, text=text)
    mask.setX(mask.getX().getValue()+x_offset)
    mask.setY(mask.getY().getValue()+y_offset)
    roi = omero.model.RoiI()
    roi.addShape(mask)
    return roi
  except:
    print(f"Mask creation failed for {mask_path}")
    return None


def save_mask(roi, img, conn):
  us = conn.getUpdateService()
  roi.setImage(img)
  return us.saveAndReturnObject(roi)


def main(conn):
  # example file name:
  # /.../mask/na/m116/150414_m116/22-Feb-2018_m116_s12_t60_x736_y1467_t212/MASK_22-Feb-2018_m116_s12_t60_x736_y1467_t212_t7Ready_f00111.tif
  FORMAT = "mask/(.+)/(.+)/(.+)/.+/(.+)"
  #              high/low       xyz
  #                   celltype     filename
  #                        img_name

  # MASK_22-Feb-2018_m116_s12_t60_x736_y1467_t212_t7Ready_f00111.tif
  MASK_FORMAT = ".*_s(\d\d)_t(\d+)_x(\d+)_y(\d+)_t(\d+)_.+f(\d+)"

  i = 0
  c = 0
  entries = open(maskpaths, 'r').readlines()
  for entry in entries:
    entry = entry.strip()
    i += 1
    fmatch = re.search(FORMAT, entry, re.IGNORECASE)
    if fmatch:
      high_low = fmatch.group(1)
      cell_type = fmatch.group(2)
      img_name = fmatch.group(3)
      filename = fmatch.group(4)
      rmatch = re.search(MASK_FORMAT, filename, re.IGNORECASE)
      if rmatch:
        s = rmatch.group(1)
        # 150414_m116.nd2 [150414_m116.nd2 (series 01)]
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
          mask = create_mask(entry, x, y, t, f"{cell_type}, {high_low}")
          if mask and not DRYRUN:
            try:
              roi = save_mask(mask, img, conn)
              print(f"Saved ROI ({roi.getId().getValue()}) for image {img_name}")
              c += 1
            except:
              print(f"Saving Mask for image {img_name} failed!")
          else:
            print(f"Created Mask for image {img_name} (dry run)")
        except:
          print(f"Image {img_name} not found!")
      else:
        "Unexpected format\nline: {entry}"
    else:
      "Unexpected format\nline: {entry}"
    print(f"({i}/1706003)")
  print(f"Created {c} Masks")


if __name__ == '__main__':
  host = os.environ.get('OMERO_HOST', 'localhost')
  port = os.environ.get('OMERO_PORT', '4064')
  user = os.environ.get('OMERO_USER', 'NA')
  pw = os.environ.get('OMERO_PASSWORD', 'NA')
  with BlitzGateway(user, pw, host=host, port=port) as conn:
    main(conn)
