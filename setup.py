from distutils.core import setup

try:
    import pypandoc
    LONG_DESCRIPTION = pypandoc.convert('README.md', 'rst')
except (IOError, ImportError):
    with open('README.md') as infile:
        LONG_DESCRIPTION = infile.read()

setup(
    name='soupy',
    py_modules=['soupy'],
    version='0.2',
    long_description=LONG_DESCRIPTION,
    description='Easier wrangling of web documents',
    author='chrisnbeaumont@gmail.com',
    author_email='chrisnbeaumont@gmail.com',
    url='http://github.com/ChrisBeaumont/soupy',
    classifiers=[
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'License :: OSI Approved :: MIT License',
    ],
)
