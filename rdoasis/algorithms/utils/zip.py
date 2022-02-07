from typing import Generator

from zipstream import ZipFile as BaseZipFile


class StreamingZipFile(BaseZipFile):
    """Extend the ZipFile class to provide support for true streaming zips."""

    def write_from_generator(self, generator: Generator):
        """Write data from a generator of paths to write."""
        self.paths_to_write = generator
