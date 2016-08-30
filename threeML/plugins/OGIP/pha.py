import os
import astropy.io.fits as pyfits
import numpy as np
import warnings

_required_keywords = {}
_required_keywords['observed'] = ("mission:TELESCOP,instrument:INSTRUME,filter:FILTER," +
                                "exposure:EXPOSURE,backfile:BACKFILE," +
                                "respfile:RESPFILE," +
                                "ancrfile:ANCRFILE,hduclass:HDUCLASS," +
                                "hduclas1:HDUCLAS1,poisserr:POISSERR," +
                                "chantype:CHANTYPE,detchans:DETCHANS,"
                                "backscal:BACKSCAL").split(",")

# hduvers:HDUVERS

_required_keywords['background'] = ("mission:TELESCOP,instrument:INSTRUME,filter:FILTER," +
                                  "exposure:EXPOSURE," +
                                  "hduclass:HDUCLASS," +
                                  "hduclas1:HDUCLAS1,poisserr:POISSERR," +
                                  "chantype:CHANTYPE,detchans:DETCHANS,"
                                  "backscal:BACKSCAL").split(",")

# hduvers:HDUVERS

_might_be_columns = {}
_might_be_columns['observed'] = ("EXPOSURE,BACKFILE," +
                              "CORRFILE,CORRSCAL," +
                              "RESPFILE,ANCRFILE,"
                              "BACKSCAL").split(",")
_might_be_columns['background'] = ("EXPOSURE,BACKSCAL").split(",")


class PHA(object):
    """
    Represents a PHA spectrum from the OGIP format. While this class will always represents only one spectrum, it can
    be instances with both a Type I and Type II file.

    Despite the input (counts or rates), this will always have data expressed in rates.
    """

    def __init__(self, phafile, spectrum_number=None, file_type='observed'):

        if '.root' not in phafile:

            self._init_from_FITS(phafile, spectrum_number, file_type)

        else:

            self._init_from_ROOT()

    def _init_from_ROOT(self):

        # This will be needeed for the VERITAS plugin

        raise NotImplementedError("Not yet implemented")

    def _init_from_FITS(self, phafile, spectrum_number, file_type='observed'):

        assert file_type.lower() in ['observed', 'background'], "Unrecognized filetype keyword value"

        self._file_type = file_type.lower()

        # Allow the use of a syntax like "mySpectrum.pha{1}" to specify the spectrum
        # number in PHA II files

        ext = os.path.splitext(phafile)[-1]

        if '{' in ext:

            spectrum_number = int(ext.split('{')[-1].replace('}', ''))

            phafile = phafile.split('{')[0]

        # Read the data

        with pyfits.open(phafile) as f:

            try:

                HDUidx = f.index_of("SPECTRUM")

            except:

                raise RuntimeError("The input file %s is not in PHA format" % (phafile))

            self._spectrum_number = spectrum_number

            spectrum = f[HDUidx]
            data = spectrum.data
            header = spectrum.header

            # We don't support yet the rescaling

            if "CORRFILE" in header:

                if header.get("CORRFILE").upper().strip() != "NONE":

                    raise RuntimeError("CORRFILE is not yet supported")

            # Determine if this file contains COUNTS or RATES

            if "COUNTS" in data.columns.names:

                self._has_rates = False
                self._data_column_name = "COUNTS"

            elif "RATE" in data.columns.names:

                self._has_rates = True
                self._data_column_name = "RATE"

            else:

                raise RuntimeError("This file does not contain a RATE nor a COUNTS column. "
                                   "This is not a valid PHA file")

            # Determine if this is a PHA I or PHA II
            if len(data.field(self._data_column_name).shape) == 2:

                self._typeII = True

                if self._spectrum_number == None:

                    raise RuntimeError("This is a PHA Type II file. You have to provide a spectrum number")

            else:

                self._typeII = False

            # Collect informations from mandatory keywords

            keys = _required_keywords[self._file_type]

            self._gathered_keywords = {}

            for k in keys:

                internal_name, keyname = k.split(":")

                key_has_been_collected = False

                if keyname in header:

                    self._gathered_keywords[internal_name] = header.get(keyname)

                    key_has_been_collected = True

                # Note that we check again because the content of the column can override the content of the header

                if keyname in _might_be_columns[self._file_type] and self._typeII:

                    # Check if there is a column with this name

                    if keyname in data.columns.names:

                        # This will set the exposure, among other things

                        self._gathered_keywords[internal_name] = data[keyname][self._spectrum_number - 1]

                        key_has_been_collected = True

                if not key_has_been_collected:

                    # The keyword POISSERR is a special case, because even if it is missing,
                    # it is assumed to be False if there is a STAT_ERR column in the file

                    if keyname == "POISSERR" and "STAT_ERR" in data.columns.names:

                        warnings.warn("POISSERR is not set. Assuming non-poisson errors as given in the "
                                      "STAT_ERR column")

                        self._gathered_keywords['poisserr'] = False

                    elif keyname == "ANCRFILE":

                        # Some non-compliant files have no ARF because they don't need one. Don't fail, but issue a
                        # warning

                        warnings.warn("ANCRFILE is not set. This is not a compliant OGIP file. Assuming no ARF.")

                        self._gathered_keywords['ancrfile'] = "NONE"

                    else:

                        raise RuntimeError("Keyword %s not found. File %s is not a proper PHA "
                                           "file" % (keyname, phafile))

            # Now get the data (counts or rates) and their errors. If counts, transform them in rates

            if self._typeII:

                # PHA II file
                if self._has_rates:

                    self._rates = data.field(self._data_column_name)[self._spectrum_number - 1, :]

                    if not self.is_poisson():

                        self._rate_errors = data.field("STAT_ERR")[self._spectrum_number - 1, :]

                else:

                    self._rates = data.field(self._data_column_name)[self._spectrum_number - 1, :] / self.exposure

                    if not self.is_poisson():

                        self._rate_errors = data.field("STAT_ERR")[self._spectrum_number - 1, :] / self.exposure


                if "SYS_ERR" in data.columns.names:

                    self._sys_errors = data.field("SYS_ERR")[self._spectrum_number - 1, :]
                else:

                    self._sys_errors = np.zeros(self._rates.shape)


            elif self._typeII == False:

                # PHA 1 file
                if self._has_rates:

                    self._rates = data.field(self._data_column_name)

                    if not self.is_poisson():

                        self._rate_errors = data.field("STAT_ERR")

                else:

                    self._rates = data.field(self._data_column_name) / self.exposure

                    if not self.is_poisson():

                        self._rate_errors = data.field("STAT_ERR") / self.exposure

                if "SYS_ERR" in data.columns.names:

                    self._sys_errors = data.field("SYS_ERR")

                else:

                    self._sys_errors = np.zeros(self._rates.shape)

        # Now that we have read it, some safety checks

        assert self._rates.shape[0] == self._gathered_keywords['detchans'], \
            "The data column (RATES or COUNTS) has a different number of entries than the " \
            "DETCHANS declared in the header"

    @property
    def rates(self):
        """
        :return: rates per channel
        """
        return self._rates

    @property
    def rate_errors(self):
        """
        If the spectrum has no Poisson error (POISSER is False in the header), this will return the STAT_ERR column
        :return: errors on the rates
        """

        assert self.is_poisson == False, "Cannot request errors on rates for a Poisson spectrum"

        return self._rate_errors

    @property
    def n_channels(self):

        return self._gathered_keywords['detchans']

    @property
    def sys_errors(self):
        """
        Systematic errors per channel. This is nonzero only if the SYS_ERR column is present in the input file.

        :return: the systematic errors stored in the input spectrum
        """
        return self._sys_errors

    @property
    def exposure(self):
        """
        Exposure in seconds

        :return: exposure
        """
        return self._gathered_keywords['exposure']

    def _return_file(self, key):

        value = self._gathered_keywords[key]

        if value is None or value.upper() == 'NONE':

            return None

        else:

            return value

    @property
    def background_file(self):
        """
        Returns the background file definied in the header, or None if there is none defined

        :return: a path to a file, or None
        """

        return self._return_file('backfile')

    @property
    def scale_factor(self):
        """
        This is a scale factor (in the BACKSCAL keyword) which must be used to rescale background and source
        regions

        :return:
        """
        return self._gathered_keywords['backscal']

    @property
    def response_file(self):
        """
            Returns the response file definied in the header, or None if there is none defined

            :return: a path to a file, or None
            """
        return self._return_file('respfile')

    @property
    def ancillary_file(self):
        """
            Returns the ancillary file definied in the header, or None if there is none defined

            :return: a path to a file, or None
            """
        return self._return_file('ancrfile')

    def is_poisson(self):
        """
        Returns whether the spectrum has Poisson errors or not

        :return: True or False
        """

        return self._gathered_keywords['poisserr']