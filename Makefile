

ipynb : nb_proc/RowlandGeometry.ipynb nb_proc/Placethedetector.ipynb nb_proc/Subaperturing.ipynb nb_proc/Tolerances.ipynb nb_proc/Chirp.ipynb nb_proc/basicflat.ipynb

nb_proc/%.ipynb : notebooks/%.ipynb
	mkdir -p nb_proc
	# Set kernel name to how the kernel is called when inside the environment
	# Notebook meta data may have global kernel name
	# Note output dir is relative to input dir
	# so we build in same dir and use ../$@
	cd notebooks && jupyter nbconvert --ExecutePreprocessor.kernel_name=python3 --ExecutePreprocessor.timeout=3600 --to notebook --execute $(notdir $<) --output ../$@
