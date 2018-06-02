#!/usr/bin/env python2

import os
import grass.script as gscript
from PIL import Image

# User input
input_image=[]
input_image.append("Illustration/image_1.jpg")
input_image.append("Illustration/image_2.jpg")


def main(input_image):
	# Initiate a list for temp layers and groups
	TMP=[]
	TMP_file=[]
	TMP_region=[]
	TMP_group=[]

	# Tranform image in .png if needed
	filepath,extension=os.path.splitext(input_image)
	if extension != ".png":
		im=Image.open(input_image)
		im.save(filepath+".png")
		input_image=filepath+".png"
		TMP_file.append(input_image)

	# Import .png image in GRASS
	tmp_image=os.path.split(gscript.tempfile())[1] # Generate a name for temporary layer
	TMP.append(tmp_image)
	gscript.run_command('r.in.png', overwrite=True, input=input_image, output=tmp_image)

	# Create a list of layers corresponding to RGB of the image 
	list_layers=gscript.list_strings("rast", pattern=tmp_image, flag="r")
	[TMP.append(a) for a in list_layers]

	# Set computional region and save it with name
	tmp_region='region_'+tmp_image
	gscript.run_command('g.region', raster=list_layers[0], save=tmp_region)
	TMP_region.append(tmp_region)

	# Create a image group
	tmp_group=os.path.split(gscript.tempfile())[1] # Generate a name for temporary group
	TMP_group.append(tmp_group)
	gscript.run_command('i.group', group=tmp_group, input=",".join(list_layers))

	# Unsupervised segmentation parameters optimization
	gscript.run_command('i.segment.uspo', overwrite=True, group=tmp_group, output='-', segment_map='best', regions=tmp_region,
						segmentation_method='region_growing', threshold_start='0.005', threshold_stop='0.4', threshold_step='0.01',
						minsizes='50', memory='5000', processes='15')
	TMP.append('best_'+tmp_region+'_rank1')

	# Compute mean spectral value per segment
	rbg_layer={}
	rbg_layer_mean={}
	for layer in list_layers:
		outputname=layer.split("@")[0]+'_avg'
		gscript.run_command('r.stats.zonal', overwrite=True, base='best_'+tmp_region+'_rank1',
				cover=layer, method='average', output=outputname)
		TMP.append(outputname)
		# Create a dictionary containing name of RBG layer
		if outputname.split("_")[0].split(".")[-1]=="r":
			rbg_layer['r']=layer
			rbg_layer_mean['r']=outputname
		elif outputname.split("_")[0].split(".")[-1]=="g":
			rbg_layer['g']=layer
			rbg_layer_mean['g']=outputname
		elif outputname.split("_")[0].split(".")[-1]=="b":
			rbg_layer['b']=layer
			rbg_layer_mean['b']=outputname

	# Create a RGB composite as a new layer
	composite=os.path.split(filepath)[-1]
	composite_final=composite+"_final"
	gscript.run_command('r.composite', overwrite=True, red=rbg_layer['r'], green=rbg_layer['g'], blue=rbg_layer['b'], output=composite)
	gscript.run_command('r.composite', overwrite=True, red=rbg_layer_mean['r'], green=rbg_layer_mean['g'], blue=rbg_layer_mean['b'], output=composite_final)

	# Output layer as .png file
	gscript.run_command('r.out.png', overwrite=True, input=composite_final, output=filepath+"_uspo.png")

	# Cleanup 
	gscript.run_command('g.remove', flags='f', type='raster', name=','.join(TMP))
	gscript.run_command('g.remove', flags='f', type='region', name=','.join(TMP_region))
	gscript.run_command('g.remove', flags='f', type='group', name=','.join(TMP_group))
	for f in TMP_file:
		os.remove(f)
		
# MAIN
for image in input_image:
	main(image)
