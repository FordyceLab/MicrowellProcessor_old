# title             : chipcollections.py
# description       : 
# authors           : Daniel Mokhtari
# credits           : Craig Markin
# date              : 20180615
# version update    : 20180615
# version           : 0.1.0
# usage             : With permission from DM
# python_version    : 3.6

# General Python
import os
import logging
from glob import glob
from pathlib import Path
from collections import namedtuple, OrderedDict
import pandas as pd

from tqdm import tqdm
from skimage import external

from chip import ChipImage



class ChipSeries:
    def __init__(self, device, series_index, attrs = None):
        """
        Constructor for a ChipSeries object.

        Arguments:
            (experiment.Device) device: 
            (int) series_index:
            (dict) attrs: arbitrary ChipSeries metdata

        Returns:
            Return

        """

        self.device = device # Device object
        self.attrs = attrs # general metadata fro the chip
        self.series_indexer = series_index
        self.description = description
        self.chips = {}
        self.series_root = None
        logging.debug('ChipSeries Created | {}'.format(self.__str__()))


    def add_file(self, identifier, path, channel, exposure):
        """
        Adds a ChipImage of the image at path to the ChipSeries, mapped from the passed identifier.
        
        Arguments:
            (Hashable) identifier: a unique chip identifier
            (str) path: image file path
            (str) channel: imaging channel
            (int) exposure: imaging exposure time (ms)

        Returns:
            None

        """

        source = Path(path)
        chipParams = (self.device.corners, self.device.pinlist, channel, exposure)
        self.chips[identifier] = ChipImage(self.device, source, {self.series_indexer:identifier}, *chipParams)
        logging.debug('Added Chip | Root: {}/, ID: {}'.format(source, identifier))


    def load_files(self, root, channel, exposure, indexes = None, custom_glob = None):
        """
        Loads indexed images from a directory as ChipImages. 
        Image filename stems must be of the form *_index.tif. 
        
        Arguments:
            (str) root: directory path containing images
            (str) channel: imaging channel
            (int) exposure: imaging exposure time (ms)
            (list | tuple) indexes: custom experimental inde

        Returns:
            None

        """

        self.series_root = root
        
        glob_pattern = '*StitchedImg*.tif'
        if custom_glob:
            glob_pattern = custom_glob
        
        if not indexes:
            r = Path(root)
            img_files = [i for i in list(r.glob(glob_pattern)) if not 'ChamberBorders'in i.stem or 'Summary' in i.stem]
            img_paths = [Path(os.path.join(r.parent, img)) for img in img_files]
            record = {int(path.stem.split('_')[-1]):path for path in img_paths}
            chipParams = (self.device.corners, self.device.pinlist, channel, exposure)
            self.chips = {identifier:ChipImage(self.device, source, {self.series_indexer:identifier}, *chipParams) for identifier, source in record.items()}
            
            keys = list(self.chips.keys())
            logging.debug('Loaded Series | Root: {}/, IDs: {}'.format(root, keys))


    def summarize(self):
        """
        Summarize the ChipSeries as a Pandas DataFrame for button and/or chamber features
        identified in the chips contained.

        Arguments:
            None

        Returns:
            (pd.DataFrame) summary of the ChipSeries

        """

        summaries = []
        for i, r in self.chips.items():
            df = r.summarize()
            df[self.series_indexer] = i
            summaries.append(df)
        return pd.concat(summaries).sort_index()


    def map_from(self, reference, mapto_args = {}):
        """
        Maps feature positions from a reference chip.ChipImage to each of the ChipImages in the series.
        Specific features can be mapped by passing the optional mapto_args to the underlying 
        mapper.

        Arguments:
            (chip.ChipImage) reference: reference image (with found button and/or chamber features)
            (dict) mapto_args: dictionary of keyword arguments passed to ChipImage.mapto().

        Returns:
            None

        """

        for chip in tqdm(self.chips.values(), desc = 'Series <{}> Stamped and Mapped'.format(self.description)):
            chip.stamp()
            reference.mapto(chip, **mapto_args)


    def from_record():
        """
        TODO: Import imaging from a Stitching record.
        """
        return


    def _repr_pretty_(self, p, cycle = True):
        p.text('<{}>'.format(self.device.__str__()))


    def save_summary(self, outPath = None):
        """
        Generates and exports a ChipSeries summary Pandas DataFrame as a bzip2 compressed CSV file.
        
        Arguments:
            (str) outPath: target directory for summary

        Returns:
            None

        """

        target = self.series_root
        if outPath:
            target = outPath
        df = self.summarize()
        fn = '{}_{}_{}.csv.bz2'.format(self.device.dname, self.description, 'ChipSeries')
        df.to_csv(os.path.join(target, fn), compression = 'bz2')


    def save_summary_images(self, outPath = None, featuretype = 'chamber'):
        """
        Generates and exports a stamp summary image (chip stamps concatenated)
        
        Arguments:
            (str) outPath: user-define export target directory
            (str) featuretype: type of feature overlay ('chamber' | 'button')

        Returns:
            None

        """

        target_root = self.series_root
        if outPath:
            target_root = outPath
        target = os.path.join(target_root, 'SummaryImages') # Wrapping folder
        os.makedirs(target, exist_ok=True)
        for c in self.chips.values():
            image = c.summary_image(featuretype)
            name = '{}_{}.tif'.format('Summary', c.data_ref.stem)
            outDir = os.path.join(target, name)
            external.tifffile.imsave(outDir, image)
        logging.debug('Saved Summary Images | Series: {}'.format(self.__str__()))


    def _delete_stamps(self):
        """
        Deletes and forces garbage collection of stamps for all ChipImages
        
        Arguments:
            None

        Returns:
            None

        """

        for c in self.chips.values():
            c._delete_stamps()


    def repo_dump(self, target_root, title, as_ubyte = False, featuretype = 'button'):
        """
        Save the chip stamp images to the target_root within folders title by chamber IDs

        Arguments:
            (str) target_root:
            (str) title:
            (bool) as_ubyte:

        Returns:
            None

        """

        for i, c in self.chips.items():
            title = '{}{}_{}'.format(self.device.setup, self.device.dname, i)
            c.repo_dump(featuretype, target_root, title, as_ubyte = as_ubyte)

    def __str__(self):
        return ('Description: {}, Device: {}'.format(self.description, str((self.device.setup, self.device.dname))))



class StandardSeries(ChipSeries):
    def __init__(self, device, description, attrs = None):
        """
        Constructor for a StandardSeries object.

        Arguments:
            (experiment.Device) device: Device object
            (str) description: Terse description (e.g., 'cMU')
            (dict) attrs: arbitrary StandardSeries metadata

        Returns:
            None

        """

        self.device = device # Device object
        self.attrs = attrs # general metadata fro the chip
        self.series_indexer = 'concentration_uM'
        self.description = description
        self.chips = None
        self.series_root = None
        logging.debug('StandardSeries Created | {}'.format(self.__str__()))
    
    def get_hs_key(self):
        return max(self.chips.keys())

    def get_highstandard(self):
        """
        Gets the "maximal" (high standard) chip object key

        Arguments:
            None

        Returns:
            None

        """


        return self.chips[self.get_hs_key()]
    

    def map_from_hs(self, mapto_args = {}):
        """
        Maps the chip image feature position from the StandardSeries high standard to each 
        other ChipImage
        
        Arguments:
            (dict) mapto_args: dictionary of keyword arguments passed to ChipImage.mapto().

        Returns:
            None

        """

        reference_key = {self.get_hs_key()}
        all_keys = set(self.chips.keys())
        hs = self.get_highstandard()
        
        for key in tqdm(all_keys - reference_key, desc = 'Processing Standard <{}>'.format(self.__str__())):
            self.chips[key].stamp()
            hs.mapto(self.chips[key], **mapto_args)


    def process(self, featuretype = 'chamber'):
        """
        A high-level (script-like) function to execute analysis of a loaded Standard Series.
        Processes the high-standard (stamps and finds chambers) and maps processed high standard
        to each other ChipImage
        
        Arguments:
            (str) featuretype: stamp feature to map

        Returns:
            None

        """

        hs = self.get_highstandard()
        hs.stamp()
        hs.findChambers()
        self.map_from_hs(mapto_args = {'features': featuretype})
    

    def process_summarize(self):
        """
        Simple wrapper to process and summarize the StandardSeries Data

        Arguments:
            None

        Returns:
            None

        """

        self.process()
        df =  self.summarize()
        return df


    def save_summary(self, outPath = None):
        """
        Generates and exports a StandardSeries summary Pandas DataFrame as a bzip2 compressed CSV file.
        
        Arguments:
            (str | None) outPath: target directory for summary. If None, saves to the series root.

        Returns:
            None

        """

        target = self.series_root
        if outPath:
            target = outPath
        df = self.summarize()
        fn = '{}_{}_{}.csv.bz2'.format(self.device.dname, self.description, 'StandardSeries_Analysis')
        df.to_csv(os.path.join(target, fn), compression = 'bz2')
        logging.debug('Saved StandardSeries Summary | Series: {}'.format(self.__str__()))



class Timecourse(ChipSeries):
    def __init__(self, device, description, attrs = None):
        """
        Constructor for a Timecourse object.

        Arguments:
            (experiment.Device) device:
            (str) description: user-define description
            (dict) attrs: arbitrary metadata

        Returns:
            None
        
        """

        self.device = device # Device object
        self.attrs = attrs # general metadata fro the chip
        self.description = description
        self.series_indexer = 'time_s'
        self.chips = None
        self.series_root = None
        logging.debug('Timecourse Created | {}'.format(self.__str__()))


    def process(self, chamber_reference, featuretype = 'chamber'):
        """
        Map chamber positions (stamp, feature mapping) from the provided reference

        Arguments:
            (ChipImage) chamber_reference: reference ChipImage for chamber position mapping
            (str) featuretype: type of feature to map ('chamber' | 'button' | 'all')

        Returns:
            None

        """

        self.map_from(chamber_reference, mapto_args = {'features': featuretype})


    def process_summarize(self, chamber_reference):
        """
        
        Process (stamp, positions and features mapping) and summarize the resulting image data
        as a Pandas DataFrame
        
        Arguments:
            (ChipImage) chamber_reference: reference ChipImage for chamber position mapping

        Returns:
            (pd.DataFrame) DataFrame of chip feature information

        """

        self.process(chamber_reference)
        df =  self.summarize()
        return df


    def save_summary(self, outPath = None):
        """
        
        Arguments:
            (str) outPath: target directory for summary

        Returns:
            None

        """

        target = self.series_root
        if outPath and os.isdir(outPath):
            target = outPath
        df = self.summarize()
        fn = '{}_{}_{}.csv.bz2'.format(self.device.dname, self.description, 'Timecourse')
        df.to_csv(os.path.join(target, fn), compression = 'bz2')
        logging.debug('Saved Timecourse Summary | Timecourse: {}'.format(self.__str__()))



class Titration(ChipSeries):
    # TODO
    pass



class ChipQuant:
    def __init__(self, device, description, attrs = None):
        """
        Constructor for a ChipQuant object
       
        Arguments:
            (experiment.Device) device: device object
            (str) description: terse user-define description
            (dict) attrs: arbitrary metadata

        Returns:
            None

        """

        self.device = device
        self.description = description
        self.attrs = attrs
        self.chip = None
        self.processed = False
        logging.debug('ChipQuant Created | {}'.format(self.__str__()))


    def load_file(self, path, channel, exposure):
        """
        Loads an image file as a ChipQuant.
        
        Arguments:
            (str) path: path to image
            (str) channel: imaging channel
            (int) exposure: exposure time (ms)

        Returns:
            None

        """

        p = Path(path)
        chipParams = (self.device.corners, self.device.pinlist, channel, exposure)
        self.chip = ChipImage(self.device, p, {}, *chipParams)
        logging.debug('ChipQuant Loaded | Description: {}'.format(self.description))


    def process(self, reference = None, mapped_features = 'button'):
        """
        Processes a chip quantification by stamping and finding buttons. If a reference is passed,
        button positions are mapped.
        
        Arguments:
            (ChipImage) button_ref: Reference ChipImage
            (st) mapped_features: features to map from the reference (if button_ref)

        Returns:
            None

        """

        self.chip.stamp()
        if not reference:
            if mapped_features == 'button':
                self.chip.findButtons()
            elif mapped_features == 'chamber':
                self.chip.findChambers()
            elif mapped_features == 'all':
                self.chip.findButtons()
                self.chip.findChambers()
            else:
                raise ValueError('Must specify valid feature name to map ("button", "chamber", or "all"')
        else:
            reference.mapto(self.chip, features = mapped_features)
        self.processed = True
        logging.debug('Buttons Processed | {}'.format(self.__str__()))


    def summarize(self):
        """
        Summarize the ChipQuant as a Pandas DataFrame for button features
        identified in the chips contained.

        Arguments:
            None

        Returns:
            (pd.DataFrame) summary of the ChipSeries

        """

        if self.processed:
            return self.chip.summarize()
        else:
            raise ValueError('Must first Process ChipQuant')


    def process_summarize(self, reference = None, process_kwrds = {}):
        """
        Script-like wrapper for process() and summarize() methods
        
        Arguments:
            (chip.ChipImage) reference: ChipImage to use as a reference
            (dict) process_kwrds: keyword arguments passed to ChipQuant.process()

        Returns:
            (pd.DataFrame) summary of the ChipSeries
        

        """
        self.process(reference = reference, **process_kwrds)
        return self.summarize()


    def save_summary_image(self, outPath_root = None):
        """
        Generates and exports a stamp summary image (chip stamps concatenated)

        Arguments:
            (str) outPath_root: path of user-defined export root directory

        Returns:
            None

        """

        outPath = self.chip.data_ref.parent
        if outPath_root:
            if not os.isdir(outPath_root):
                em = 'Export directory does not exist: {}'.format(outPath_root)
                raise ValueError(em)
            outPath = Path(outPath_root)

        target = os.path.join(outPath, 'SummaryImages') # Wrapping folder
        os.makedirs(target, exist_ok=True)
        
        c = self.chip
        image = c.summary_image('button')
        name = '{}_{}.tif'.format('Summary', c.data_ref.stem)
        outDir = os.path.join(target, name)
        external.tifffile.imsave(outDir, image)
        logging.debug('Saved ChipQuant Summary Image | ChipQuant: {}'.format(self.__str__()))


    def repo_dump(self, outPath_root, as_ubyte = False):
        """
        Export the ChipQuant chip stamps to a repository (repo). The repo root contains a 
        directory for each unique pinlist identifier (MutantID, or other) and subdirs
        for each chamber index. Stamps exported as .png
        
        Arguments:
            (str): outPath_root: path of user-defined repo root directory
            (bool) as_ubyte: flag to export the stamps as uint8 images

        Returns:
            None

        """

        title = '{}{}_{}'.format(self.device.setup, self.device.dname, self.description)
        self.chip.repo_dump('button', outPath_root, title, as_ubyte = as_ubyte)
    

    def __str__(self):
        return ('Description: {}, Device: {}'.format(self.description, str((self.device.setup, self.device.dname))))


class Assay:
    def __init__(self, device, description, attrs = None):
        """
        Constructor for an Assay class.

        Arguments:
            (experiment.Device) device:
            (str) description: user-defined assay description
            (dict) attrs: arbitrary metadata

        Returns:
            None

        """

        self.device = device # Device object
        self.attrs = attrs # general metadata fro the chip
        self.description = description
        self.series = None
        self.quants = []

    def add_series(self, c):
        """
        Setter to add an arbitary ChipSeries to the assay

        Arguments:
            (ChipSeries) c: a chipseries (or subclass)

        Returns:
            None

        """

        if isinstance(c, ChipSeries):
            self.series = c
        else:
            raise TypeError('Must provide a valid ChipSeries')

    def add_quant(self, c):
        """
        Setter to add an arbitry ChipQuant to the Assay.

        Arguments:
            (ChipQuant) c: a chipquant

        Returns:
            None
        

        """
        self.quants.append(c)


class TurnoverAssay(Assay):
    
    def merge_summarize(self):
        """
        A script-like method to summarize each quantification and join them with summary 
        of the ChipSeries.

        Arguments:
            None

        Returns:
            (pd.DataFrame) a Pandas DataFrame summarizing the Assay

        """

        quants_cleaned = []
        for quant in self.quants:
            desc = quant.description
            summary = quant.chip.summarize()
            toAdd = summary.drop(columns = ['id'])
            quants_cleaned.append(summary.add_suffix('_{}'.format(desc.replace(' ', '_'))))
        
        kinSummary = self.series.summarize()
        merged = kinSummary.join(quants_cleaned, how='left', lsuffix='_kinetic', rsuffix='_buttonquant')
        return merged



class AssaySeries:
    def __init__(self, device, descriptions, chamber_ref, button_ref, attrs = None, assays_attrs = []):
        """
        Constructor for and AssaySeries, a high-level class representing a collection of related TurnoverAssays. 
        Holds arbitrary ordered TurnoverAssays as a dictionary. Designed specficially for eMITOMI use. 
        TurnoverAssays are generated when the object is constructed, but must be populated after with 
        kinetic and quantificationd data.

        Arguments:
            (experiment.Device) device: Device object
            (list | tuple) descriptions: Descriptions assocated with assays
            (chip.ChipImage) chamber_ref: a ChipImage object with found chambers for referencing
            (ChipQuant) button_ref: a ChipQuant object with found buttons for referencing
            (dict) attrs:arbitrary StandardSeries metadata

        Returns:
            None

        """

        self.device = device
        self.assays = OrderedDict([(description, TurnoverAssay(device, description)) for description in descriptions])
        self.chamber_ref = chamber_ref
        self.button_ref = button_ref
        self.chamber_root = None
        self.button_root = None
        self.attrs = attrs
        logging.debug('AssaySeries Created | {}'.format(self.__str__()))
        logging.debug('AssaySeries Chamber Reference Set | {}'.format(chamber_ref.__str__()))
        logging.debug('AssaySeries Button Reference Set | {}'.format(button_ref.__str__()))


    def load_kin(self, descriptions, paths, channel, exposure): 
        """
        Loads kinetic imaging and descriptions into the AssaySeries.

        Given paths of imaging root directories, creates Timecourse objects and associates with 
        the passed descriptions. Descriptions and paths must be of equal length. Descriptions and 
        paths are associated on their order (order matters)

        Arguments:
            (list | tuple) descriptions: descriptions of the imaging (paths)
            (list | tuple) paths: paths to directories containing timecourse imaging
            (str) channel: imaging channel
            (int) exposure: exposure time (ms)

        Returns:
            None

        """

        len_series = len(self.assays)
        len_descriptions = len(descriptions)

        if len_descriptions != len_series:
            raise ValueError('Descriptions and series of different lengths. Number of assays and descriptions must match.')
        kin_refs = list(zip(descriptions, paths, [channel]*len_series, [exposure]*len_series))
        for desc, p, chan, exp in kin_refs:
            t = Timecourse(self.device, desc)
            t.load_files(p, chan, exp)
            self.assays[desc].series = t


    def load_quants(self, descriptions, paths, channel, exposure):
        """
        Loads chip quantification imaging and associates with Timecourse data for existing Assay objects
        
        Arguments:
            (list | tuple) descriptions: descriptions of the imaging (paths)
            (list | tuple) paths: paths to directories containing quantification imaging
            (str) channel: imaging channel
            (int) exposure: exposure time (ms)

        Returns:
            None

        """

        if len(descriptions) != len(paths):
            raise ValueError('Descriptions and paths must be of same length')
        
        len_series = len(self.assays)
        
        if len(descriptions) == 1:
            descriptions = self.assays.keys()
            paths = paths * len_series
        
        bq_refs = list(zip(descriptions, paths, [channel]*len_series, [exposure]*len_series))
        for desc, p, chan, exp in bq_refs:
            q = ChipQuant(self.device, 'Button_Quant')
            q.load_file(p, chan, exp)
            self.assays[desc].add_quant(q)


    def parse_kineticsFolders(self, root, file_handles, descriptors, channel, exposure, pattern = None):
        """
        Walks down directory tree, matches the passed file handles to the Timecourse descriptors,
        and loads kinetic imaging data. Default pattern is "*_{}*/*/StitchedImages", with {}
        file_handle

        Arguments:
            (str) root: path to directory Three levels above the StitchedImages folders (dir 
                above unique assay folders)
            (list | tuple) file_handles: unique file handles to match to dirs in the root.
            (list | tuple) descriptors: unique kinetic imaging descriptors, order-matched to
                the file_handles
            (str) channel: imaging channel
            (int) exposure: exposure time (ms)
            (bool) pattern: custom UNIX-style pattern to match when parsing dirs

        Returns:
            None

        """

        self.chamber_root = root
        if not pattern:
            pattern = "*_{}*/*/StitchedImages"
    
        p = lambda f: glob(os.path.join(root, pattern.format(f)))[0]
        files = {(handle, desc): p(handle) for handle, desc in zip(file_handles, descriptors)}

        self.load_kin(descriptors, files.values(), channel, exposure)


    def parse_quantificationFolders(self, root, file_handles, descriptors, channel, exposure, pattern = None):
        """
        Walks down directory tree, matches the passed file handles to the ChipQuant descriptors,
        and loads button quantification imaging data. Default pattern is "*_{}*/*/StitchedImages/
        BGSubtracted_StitchedImg*.tif", with {} file_handle

        Arguments:
            (str) root: path to directory Three levels above the StitchedImages folders (dir 
                above unique assay folders)
            (list | tuple) file_handles: unique file handles to match to dirs in the root.
            (list | tuple) descriptors: unique kinetic imaging descriptors, order-matched to
                the file_handles. MUST BE THE SAME USED FOR parse_kineticsFolders
            (str) channel: imaging channel
            (int) exposure: exposure time (ms)
            (bool) pattern: custom UNIX-style pattern to match when parsing dirs

        Returns:
            None

        """

        if not pattern:
            pattern = "*_{}*/*/StitchedImages/BGSubtracted_StitchedImg*.tif"
        
        try:
            p = lambda f: glob(os.path.join(root, pattern.format(f)))[0]
            files = {(handle, desc): p(handle) for handle, desc in zip(file_handles, descriptors)}
        except:
            raise ValueError('Error parsing filenames for quantifications. Glob pattern is: {}'.format(pattern))

        self.load_quants(descriptors, files.values(), channel, exposure)


    def summarize(self):
        """
        Summarizes an AssaySeries as a Pandas DataFrame.
        
        Arguments:
            None

        Returns:
            (pd.DataFrame) summary of the AssaySeries

        """

        summaries = []
        for tc in  self.assays.values():
            s = tc.merge_summarize()
            s['series_index'] = tc.description
            summaries.append(s)
        return pd.concat(summaries).sort_index()


    def process_quants(self, subset = None):
        """
        Processes the chip quantifications and saves summary images for each of, or a subset of,
        the assays.

        Arguments:
            (list | tuple) subset: list of assay descriptors (a subset of the assay dictionary keys)

        Returns:
            None

        """

        if not subset:
            subset = self.assays.keys()
        for key in tqdm(subset, desc = 'Mapping and Processing Buttons'):
            for quant in self.assays[key].quants:
                quant.process(reference = self.button_ref, mapped_features = 'button')
                quant.save_summary_image()


    def process_kinetics(self, subset = None, low_mem = True):
        """
        Processes the timecourses and saves summary images for each of, or a subset of,
        the assays.

        Arguments:
            (list | tuple) subset: list of assay descriptors (a subset of the assay dictionary keys)
            (bool) low_mem: flag to delete and garbage collect stamp data of all ChipImages
                after summarization and export

        Returns:
            None
        
        """

        if not subset:
            subset = self.assays.keys()
        for key in subset:
            s = self.assays[key].series
            s.process(self.chamber_ref)
            s.save_summary()
            s.save_summary_images(featuretype = 'chamber')
            if low_mem:
                s._delete_stamps()


    def save_summary(self, outPath = None):
        """
        Saves a CSV summary of the AssaySeries to the specified path.

        Arguments:
            (str) outPath: path of directory to save summary

        Returns:
            None

        """

        if not outPath:
            outPath = self.chamber_root
        df = self.summarize()
        fn = '{}_{}.csv.bz2'.format(self.device.dname, 'TitrationSeries_Analysis')
        df.to_csv(os.path.join(outPath, fn), compression = 'bz2')


    def __str__(self):
        return ('Assays: {}, Device: {}, Attrs: {}'.format(list(self.assays.keys()), str((self.device.setup, self.device.dname)), self.attrs))
