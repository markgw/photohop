import click

from .index import PhotoIndex
from .config import Config


@click.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False))
def main(directory):
	"""Index photos in DIRECTORY."""
	config = Config.load()
	print(f"Indexing {directory}...")
	index = PhotoIndex.index_directory(directory)
	print("Saving index")
	index.save(config)


if __name__ == '__main__':
	main()
