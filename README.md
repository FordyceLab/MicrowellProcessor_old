# MicrowellProcessor
Processes stitched microwell images to extract subarrays and save individual microwell images 

## Installation

From the command line, install github repository via 
`git clone https://github.com/FordyceLab/MicrowellProcessor`

## Usage

### Extract Subarrays

Takes in stitched grayscale image (e.g. from MicrowellStitcher) and outputs stacked .tif file of individual subarrays as well as .csv containing locations of individual microwells

**Parameters to change**
- `oc` stands for "outside corners" and is a list of the coordinates of the outer corners of the largest rectangle containing complete subarrays
  - open stitched image in ImageJ/FIJI and hover over positions to determine pixel coordinates as (x,y)
  - order of coordinates is ((top left), (top right), (bottom left), (bottom right))
  - use center of outermost microwell in each location for coordinate
  - see MicrowellProcessor/resources/oc.png for an example image
- `org_extension.INTRA_TILE_SPACING` represents the distance between microwells from adjacent subarrays
  - open stitched image in ImageJ/FIJI
  - use line function + Analyze > Measure to measure distance between center of microwells from adjacent subarrays
  - see MicrowellProcessor/resources/org_extension.INTRA_TILE_SPACING.png for example
- `subarray_dims` is the number of complete subarrays in the stitched image
  - format is (columns, rows)
  - in MicrowellProcessor/resources/oc.png, the subarray_dims parameter is (3,4)
- `tile_dims` represents the number of microwells per subarray
  - in our work, this is (20,20) for 100um microwells and (10,10) for 200um microwells
  - format is (columns, rows)
- `chip.ChipImage.stampWidth` represents the width of the individual microwell images
  - from center of blank space on one side of microwell to center of blank space on the other side, within a single subarray
  - see MicrowellProcessor/resources/chip.ChipImage.stampWidth.png for example image

All other parameters are related to file locations and are optional

### Save microwell images

Takes in stacked .tif and .csv from `extract_subarrays.ipynb` and saves individual microwell images. Includes optional code to apply basic threshold to fluorescent images and save images after threshold has been applied.

Only parameters to change here are file locations.
