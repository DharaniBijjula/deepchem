import numpy as np
from typing import Optional
from deepchem.feat import Featurizer
try:
    import pysam
except ImportError:
    pass


class SAMFeaturizer(Featurizer):
    """
    Featurizes SAM files, that store biological sequences aligned to a reference
    sequence. This class extracts Query Name, Query Sequence, Query Length,
    Reference Name,Reference Start, CIGAR and Mapping Quality of each read in
    a SAM file.

    This is the default featurizer used by SAMLoader, and it extracts the following
    fields from each read in each SAM file in the given order:-
    - Column 0: Query Name
    - Column 1: Query Sequence
    - Column 2: Query Length
    - Column 3: Reference Name
    - Column 4: Reference Start
    - Column 5: CIGAR
    - Column 6: Mapping Quality

    Examples
    --------
    >>> from deepchem.data.data_loader import SAMLoader
    >>> import deepchem as dc
    >>> inputs = 'deepchem/data/tests/example.sam'
    >>> featurizer = dc.feat.SAMFeaturizer()
    >>> features = featurizer.featurize(inputs)
    >>> type(features[0])
    <class 'numpy.ndarray'>

    Note
    ----
    This class requires pysam to be installed. Pysam can be used with Linux or MacOS X.
    To use Pysam on Windows, use Windows Subsystem for Linux(WSL).

    """

    def __init__(self, max_records=None):
        """
        Initialize SAMFeaturizer.

        Parameters
        ----------
        max_records : int or None, optional
            The maximum number of records to extract from the SAM file. If None, all records will be extracted.

        """
        self.max_records = max_records

    def _featurize(self, datapoint):
        """
        Extract features from a SAM file.

        Parameters
        ----------
        datapoint : str
            Name of SAM file.

        Returns
        -------
        features : numpy.ndarray
        A 2D NumPy array representing the extracted features.
        Each row corresponds to a SAM record, and columns represent different features.
            - Column 0: Query Name
            - Column 1: Query Sequence
            - Column 2: Query Length
            - Column 3: Reference Name
            - Column 4: Reference Start
            - Column 5: CIGAR
            - Column 6: Mapping Quality

        """

        features = []
        record_count = 0

        for record in datapoint:
            feature_vector = [
                record.query_name,
                record.query_sequence,
                record.query_length,
                record.reference_name,
                record.reference_start,
                record.cigar,
                record.mapping_quality,
            ]

            features.append(feature_vector)
            record_count += 1

            # Break the loop if max_records is set
            if self.max_records is not None and record_count >= self.max_records:
                break

        datapoint.close()

        return np.array(features, dtype="object")


class BAMFeaturizer(Featurizer):
    """
    Featurizes BAM files, that are compressed binary representations of SAM
    (Sequence Alignment Map) files. This class extracts Query Name, Query
    Sequence, Query Length, Reference Name, Reference Start, CIGAR, Mapping
    Quality, is_reverse and Query Qualities of the alignment in the BAM file.

    This is the default featurizer used by BAMLoader, and it extracts the
    following fields from each read in each BAM file in the given order:-
    - Column 0: Query Name
    - Column 1: Query Sequence
    - Column 2: Query Length
    - Column 3: Reference Name
    - Column 4: Reference Start
    - Column 5: CIGAR
    - Column 6: Mapping Quality
    - Column 7: is_reverse
    - Column 8: Query Quality Scores
    - Column 9: Pileup Information (if get_pileup=True)

    Additionally, we can also get pileups from BAM files by setting
    get_pileup=True.A pileup is a summary of the alignment of reads
    at each position in a reference sequence. Specifically, it
    provides information on the position on the reference genome,
    the depth of coverage (i.e., the number of reads aligned to that
    position), and the actual bases from the aligned reads at that
    position, along with their quality scores. This data structure
    is useful for identifying variations, such as single nucleotide
    polymorphisms (SNPs), insertions, and deletions by comparing the
    aligned reads to the reference genome. A pileup can be visualized
    as a vertical stack of aligned sequences, showing how each read
    matches or mismatches the reference at each position.
    In DeepVariant, pileups are utilized during the initial stages to
    select candidate windows for further analysis.

    Examples
    --------
    >>> from deepchem.data.data_loader import BAMLoader
    >>> import deepchem as dc
    >>> inputs = 'deepchem/data/tests/example.bam'
    >>> featurizer = dc.feat.BAMFeaturizer()
    >>> features = featurizer.featurize(inputs)
    >>> type(features[0])
    <class 'numpy.ndarray'>

    Note
    ----
    This class requires pysam to be installed. Pysam can be used with Linux or MacOS X.
    To use Pysam on Windows, use Windows Subsystem for Linux(WSL).

    """

    def __init__(self, max_records=None, get_pileup: Optional[bool] = False):
        """
        Initialize BAMFeaturizer.

        Parameters
        ----------
        max_records : int or None, optional
            The maximum number of records to extract from the BAM file. If None, all
            records will be extracted.
        get_pileup : bool, optional
            If True, pileup information will be extracted from the BAM file.
            This is used in DeepVariant. False by default.

        """
        self.max_records = max_records
        self.get_pileup = get_pileup

    def _featurize(self, datapoint):
        """
        Extract features from a BAM file.

        Parameters
        ----------
        datapoint : str
            Name of the BAM file.
            The corresponding index file must be in the same directory.

        Returns
        -------
        features : numpy.ndarray
        A 2D NumPy array representing the extracted features.

        """

        features = []
        record_count = 0

        pileup_columns = []
        initial_position = datapoint.tell()

        # This is more efficient as instead of iterating over the
        # whole file for each record, we iterate over the file once
        # and store the pileup information in a list that is
        # appended for every record.

        if self.get_pileup:
            for pileupcolumn in datapoint.pileup():
                pileup_info = {
                    "name":
                        pileupcolumn.reference_name,
                    "pos":
                        pileupcolumn.reference_pos,
                    "depth":
                        pileupcolumn.nsegments,
                    "reads": [[
                        pileupread.alignment.query_sequence,
                        pileupread.query_position, pileupread.is_del,
                        pileupread.is_refskip, pileupread.indel
                    ] for pileupread in pileupcolumn.pileups]
                }
                pileup_columns.append(pileup_info)
        datapoint.seek(initial_position)

        for record in datapoint:
            initial_position = datapoint.tell()
            feature_vector = [
                record.query_name, record.query_sequence, record.query_length,
                record.reference_name, record.reference_start, record.cigar,
                record.mapping_quality, record.is_reverse,
                np.array(record.query_qualities)
            ]

            if (self.get_pileup):
                feature_vector.append(pileup_columns)

            features.append(feature_vector)
            record_count += 1
            datapoint.seek(initial_position)

            # Break the loop if max_records is set
            if self.max_records is not None and record_count >= self.max_records:
                break

        datapoint.close()

        return np.array(features, dtype="object")


class CRAMFeaturizer(Featurizer):
    """
    Featurizes CRAM files, that are compressed columnar file format for storing
    biological sequences aligned to a reference sequence. This class extracts Query Name, Query
    Sequence, Query Length, Reference Name, Reference Start, CIGAR and Mapping
    Quality of the alignment in the CRAM file.

    This is the default featurizer used by CRAMLoader, and it extracts the following
    fields from each read in each CRAM file in the given order:-
    - Column 0: Query Name
    - Column 1: Query Sequence
    - Column 2: Query Length
    - Column 3: Reference Name
    - Column 4: Reference Start
    - Column 5: CIGAR
    - Column 6: Mapping Quality

    Examples
    --------
    >>> from deepchem.data.data_loader import CRAMLoader
    >>> import deepchem as dc
    >>> inputs = 'deepchem/data/tests/example.cram'
    >>> featurizer = dc.feat.CRAMFeaturizer()
    >>> features = featurizer.featurize(inputs)
    >>> type(features[0])
    <class 'numpy.ndarray'>

    Note
    ----
    This class requires pysam to be installed. Pysam can be used with Linux or MacOS X.
    To use Pysam on Windows, use Windows Subsystem for Linux(WSL).

    """

    def __init__(self, max_records=None):
        """
        Initialize CRAMFeaturizer.

        Parameters
        ----------
        max_records : int or None, optional
            The maximum number of records to extract from the CRAM file. If None, all
            records will be extracted.

        """
        self.max_records = max_records

    def _featurize(self, datapoint):
        """
        Extract features from a CRAM file.

        Parameters
        ----------
        datapoint : str
            Name of the CRAM file.

        Returns
        -------
        features : numpy.ndarray
        A 2D NumPy array representing the extracted features.

        """

        features = []
        record_count = 0

        for record in datapoint:
            feature_vector = [
                record.query_name,
                record.query_sequence,
                record.query_length,
                record.reference_name,
                record.reference_start,
                record.cigar,
                record.mapping_quality,
            ]

            features.append(feature_vector)
            record_count += 1

            # Break the loop if max_records is set
            if self.max_records is not None and record_count >= self.max_records:
                break

        datapoint.close()

        return np.array(features, dtype="object")


class FASTAFeaturizer(Featurizer):
    """
    Featurizes FASTA files by extracting the sequence names and sequences.
    Each sequence in the FASTA file is represented as a list containing the
    sequence name and the raw sequence itself.

    Examples
    --------
    >>> from deepchem.feat import FASTAFeaturizer
    >>> featurizer = FASTAFeaturizer()
    >>> fasta_file = 'deepchem/data/tests/example.fasta'
    >>> features = featurizer.featurize([fasta_file])
    >>> type(features[0])
    <class 'numpy.ndarray'>
    >>> features[0].shape
    (3, 2)

    Note
    ----
    This class requires pysam to be installed. Pysam can be used with Linux or MacOS X.
    To use Pysam on Windows, use Windows Subsystem for Linux(WSL).

    """

    def _featurize(self, datapoint: str, **kwargs) -> np.ndarray:
        """
        Extract features from a FASTA file.

        Parameters
        ----------
        datapoint : str
            Path to the FASTA file to be featurized.

        Returns
        -------
        np.ndarray
            A numpy array of shape (n, 2) where n is the number of sequences in the FASTA
            file. Each element is a list containing the sequence name and the sequence
            itself. The first element of each list is the sequence name (str) and the
            second element is the sequence (str).
        """
        data = []
        with pysam.FastxFile(datapoint) as fasta:
            for entry in fasta:
                data.append([entry.name, entry.sequence])
        return np.array(data, dtype=object)
