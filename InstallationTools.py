import os, glob, gzip, pickle
import configuration as conf

from Genome import Genome
from tools import UsefulFunctions as uf
from tools.CSVTools import CSVFile

def getVersion():
	"""returns pyGeno's current version"""
	return conf.pyGeno_VERSION
	
"""===These are the only function that you will need to install new features in pyGen==="""
def installGenome(packageDir, specie, genomeName) :
	gtfs = glob.glob(packageDir+'/*.gtf')
	print gtfs
	if len(gtfs) != 1 :
		raise Exception('There should be one and only one gtf index file in the package')
	
	_installSequences(packageDir, specie, genomeName)
	_installGeneSymbolIndex(gtfs[0], specie)
	
def installGenome_casava(specie, genomeName, snpsTxtFile) :
	"""Creates a light genome (contains only snps infos and no sequence from the reference genome)
	The .casavasnps files generated are identical to the casava snps but with ';' instead of tabs and 
	a single position instead of a range"""

	path = conf.DATA_PATH+'/%s/genomes/%s/'%(specie, genomeName)
	print 'Installing genome %s...' %path
	
	if not os.path.exists(path):
		os.makedirs(path)
	
	f = open(snpsTxtFile)
	lines = f.readlines()
	f.close()
	
	currChr = '-1'
	strRes = ''
	for l in lines :
		if l[0] != '#' : #ignore comments
			sl = l.replace('\t\t', '\t').split('\t')
			if sl[0] != currChr :
				if currChr != '-1' :
					f = open('%s/%s.casavasnps'%(path, currChr), 'w')
					f.write(strRes)
					f.close()
				print 'Installing snp data for %s...' % sl[0]
				currChr = sl[0]
				strRes = ''
			del(sl[0]) #remove chr
			del(sl[1]) #remove first position of the range
			strRes += ';'.join(sl)

	if currChr != '-1' :
		f = open('%s/%s.casavasnps'%(path, currChr), 'w')
		f.write(strRes)
		f.close()
	
	#print '%s/sourceFile.txt'%(path)
	f = open('%s/sourceFile.txt'%(path), 'w')
	f.write(snpsTxtFile)
	f.close()
	
	print 'Installation of genome %s/%s done.' %(specie, genomeName)


def install_dbSNP(packageFolder, specie, versionName) :
	"""To install dbSNP informations, download ASN1_flat files from the 
	dbSNP ftp : ftp://ftp.ncbi.nih.gov/snp/organisms/ and place them all in one single folder. This folder
	will be considered as a package.
	Launch this function and go make yourself a cup of coffee, this function has absolutly not been written to be fast
	
	versionName is name with wich you want to call this specific version of dbSNP
	
	pyGeno snp format is somewhat different from dbSNP's :
		- all SNPs that have a chromosome different from the one of the file, or chromosome number of '?' are discarded
		- the default value for numeric values (ex: het, se(het), 'MAF', 'GMAf count') is 0.0
		- no '?' allowed.If a numeric has a value of '?' (ex: het, se(het), 'MAF', 'GMAf count') the value is set to 0.0
		- all snps have an orientation of +. If a snp has an orientation of -, it's alleles are replaced by their complements
		- positions are 0 based
		- the only value extracted from the files are : 'posistion', 'rs', 'type', 'assembly', 'chromosome', 'validated', 'alleles', 'original_orientation', 'maf_allele', 'maf_count', 'maf', 'het', 'se(het)' 
	"""
	
	legend = ['//pos', 'chromosome', 'rs', 'type', 'alleles', 'validated', 'assembly', 'original_orientation', 'maf_allele', 'maf_count', 'maf', 'het', 'se(het)']
	#Fcts
	def fillCSV(res, csv) :
		print '\t\t sorting snps by position in chromosome...'
		l = res.keys()
		l.sort()
		print '\t\t filling CSV...'
		for pos in l :
			li = csv.addLine()
			for field in csv.legend :
				csv.set(li, field, res[pos][field.lower()])
		
	def parse(s, chroNumber, legend) :
		lines = s.split('\n')
		
		res = {}
		for field in legend :
			res[field] = ''
			
		criticalFields = ['rs', 'chromosome', '//pos', 'alleles', 'assembly', 'validated']
		numericFields = ['maf_count', 'maf', 'het', 'se(het)']
		
		for l in lines :
			sl = l.split('|')
			if sl[0][:2] == 'rs' :
				res['rs'] = sl[0][2:].strip()
				res['type'] = sl[3].strip()
			
			elif sl[0][:3] == 'SNP' and res['rs'] != None :
				res['alleles'] = sl[1].strip().replace('alleles=', '').replace("'", "")
				res['het'] = sl[2].strip().replace('het=', '')				
				res['se(het)'] = sl[3].strip().replace('se(het)=', '')
				
			elif sl[0][:3] == 'VAL' and res['rs'] != None :
				res['validated'] = sl[1].strip().replace("validated=", '')
				
			elif sl[0][:3] == 'CTG' and sl[1].find('GRCh') > -1 and res['rs'] != None :
				res['original_orientation'] = sl[-1].replace('orient=', '').strip()
				res['assembly'] = sl[1].replace('assembly=', '').strip()
				res['chromosome'] = sl[2].replace('chr=', '').strip()
				pos = sl[3].replace('chr-pos=', '').strip()
				
				if res['chromosome'] != chroNumber or pos == '?' :
					res['chromosome'] = None
					res['//pos'] = None
					return None
				
				res['//pos'] = int(pos) -1
				
			elif sl[0][:4] == 'GMAF' and res['rs'] != None :
				res['maf_allele'] = sl[1].strip().replace('allele=', '')
				res['maf_count'] = sl[2].strip().replace('count=', '')
				res['maf'] = sl[3].strip().replace('MAF=', '')
					
		for field in criticalFields :
			if res[field] == '' :
				return None
		
		for field in numericFields :
			if res[field] == '' or res[field] == '?' :
				res[field] = 0.0
			else :
				res[field] = float(res[field])
				
		if res['original_orientation'] == '-' :
			res['alleles'] = uf.complement(res['alleles'])
			
		return res
		
	#Fcts
	desc = 	"""pyGeno snp format is somewhat different from dbSNP's :
		- all SNPs that have a chromosome different from the one of the file, or chromosome number of '?' were discarded
		- the default value for numeric values (ex: het, se(het), 'MAF', 'GMAf count') is 0.0
		- no '?' allowed. If a numeric had a value of '?' (ex: het, se(het), 'MAF', 'GMAf count') the value was set to 0.0
		- all snps have an orientation of +. If a snp had an orientation of -, it's alleles were replaced by their complements
		- positions are 0 based
		- the only values extracted dbSNP files were from the files were : 'posistion', 'rs', 'type', 'assembly', 'chromosome', 'validated', 'alleles', 'original_orientation', 'maf_allele', 'maf_count', 'maf', 'het', 'se(het)'"""


	files = glob.glob(packageFolder+'/*.flat.gz')
	outPath = conf.DATA_PATH+'/%s/dbSNP/%s/' %(specie, versionName)
	if not os.path.exists(outPath):
		os.makedirs(outPath)
	
	for fil in files :
		chrStrStartPos = fil.find('ch')
		chrStrStopPos = fil.find('.flat')

		chroNumber = fil[chrStrStartPos+2: chrStrStopPos]
		outFile = fil.replace(packageFolder, outPath).replace('ds_flat_', '').replace('ch'+chroNumber, 'chr'+chroNumber).replace('.flat.gz', '.pygeno-dbSNP')
		
		print "extracting file :", fil, "..."
		f = gzip.open(fil)
		snps = f.read().split('\n\n')
		f.close()
		print snps[0]
		
		print "\tparsing..."
		
		resCSV = CSVFile(legend)
		res = {}
		for snp in snps[1:] :
			snpVals = parse(snp, chroNumber, legend)
			if snpVals != None :
				res[snpVals['//pos']] = snpVals
			
		print "\tformating data..."
		fillCSV(res, resCSV)

		print "\tsaving..."
		header = "source file : %s\n%s" % (fil, snps[0])
		header = header.split('\n')
		for i in range(len(header)) :
			header[i] = '//'+header[i]+'\n'
		header = ''.join(header)
		
		resCSV.setHeader(header)
		resCSV.save(outFile)

	readMeFile = outPath + 'README_format-description.txt'
	f = open(readMeFile, 'w')
	f.write(desc)
	f.close()

"""===These are the private functions that you should not call, unless you really know what you're doing==="""
def _installSequences(fastaDir, specie, genomeName) :
	print r"""Converting fastas from dir: %s into pyGeno's data format
	resulting files will be part of genome: %s/%s
	This may take some time, please wait...""" %(fastaDir, specie, genomeName)
	

	path = conf.DATA_PATH+'/%s/genomes/%s/'%(specie, genomeName)

	if not os.path.exists(path):
		os.makedirs(path)
		
	chrs = glob.glob(fastaDir+'/chr*.fa')
	if len(chrs) < 1 :
		raise Exception('No Fastas found in directort, installation aborted')
		
	startPos = 0
	genomeChrPos = {} 
	headers = ''
	
	for chro in chrs :
		print 'making data for Chr', chro
		
		f = open(chro)
		headers += f.readline()
		s = f.read().upper().replace('\n', '').replace('\r', '')
		f.close()
		
		fn = chro.replace('.fa', '.dat').replace(fastaDir, path)
		f = open(fn, 'w')
		f.write(s)
		f.close()
		
		ch = chro.replace(fastaDir, '').replace('/chr', '').replace('.fa', '')
		genomeChrPos[ch] = [str(ch), str(startPos), str(startPos+len(s)), str(len(s))]
		startPos = startPos+len(s)

	print 'making index file genomeChrPos'
	fh = open(path+'/genomeChrPos.index', 'w')
	fh.write('chromosome;chr_start;chr_end;length\n')
	for k in genomeChrPos.keys() :
		fh.write(';'.join(genomeChrPos[k])+'\n')
	fh.close()

	print 'writing build info file'
	f=open('%s/build_infos.txt' % (path), 'w')
	f.write('source package directory: %s' % fastaDir)
	f.write('\nheaders:\n------\n %s' % headers)
	f.close()

def _installGeneSymbolIndex(gtfFile, specie) :

	path = conf.DATA_PATH+'/%s/gene_sets/'%(specie)
	if not os.path.exists(path):
		os.makedirs(path)
		
	f = open(gtfFile)
	gtf = f.readlines()
	f.close()
	
	chroLine = 0
	chro = -1
	currChro = -1
	gtfStr = ''
	pickIndex = {}
	symbol = -1
	currSymbol = -1
	for i in range(len(gtf)) :
		sl = gtf[i].split('\t')
		currChro = sl[0]
		if chro != currChro :
			if chro != -1 :
				print '\tsaving chromosme gtf file...'
				f = open('%s/chr%s.gtf' % (path, chro), 'w')
				f.write(gtfStr)
				f.close()
				print '\tsaving chromosme pickled index...'
				f=open('%s/chr%s_gene_symbols.index.pickle' % (path, chro), 'w')
				pickle.dump(pickIndex, f, 2)
				f.close()
				print '\tdone.'
			print 'making gene symbol index for chr %s...' %chro
			
			gtfStr = ''
			pickIndex = {}
			chro = currChro
			currSymbol = -1
			symbol = -1
			chroLine = 0
			
		currSymbol = gtf[i].split('\t')[8].split(';')[3]
		currSymbol = currSymbol[currSymbol.find('"') + 1:].replace('"', '').strip()
		
		if currSymbol != symbol :
			if symbol != -1 :
				pickIndex[symbol] = "%d;%d" %(startL, chroLine)
			
			symbol = currSymbol
			startL = chroLine
		
		gtfStr += gtf[i]
		chroLine += 1

	pickIndex[symbol] = "%d;%d" %(startL, chroLine)
	print '\tsaving chromosme gtf file...'
	f = open('%s/chr%s.gtf' % (path, chro), 'w')
	f.write(gtfStr)
	f.close()
	print '\tsaving chromosme pickled index...'
	f=open('%s/chr%s_gene_symbols.index.pickle' % (path, chro), 'w')
	pickle.dump(pickIndex, f, 2)
	f.close()
	print '\tdone.'
	print 'writing build info file'
	f=open('%s/build_infos.txt' % (path), 'w')
	f.write('source file: %s' % gtfFile)
	f.close()

if __name__ == "__main__" :
	install_dbSNP('/u/daoudat/py/pyGeno/installationPackages/dbSNP/human/dbSNP137', 'human', 'dbSNP137')
	#installGenome_casava('human', 'lightR_Transcriptome', '/u/corona/Project_DSP008a/Build_Diana_ARN_R/snps.txt')
	
	#print 'install mouse'
	#installGenome('/u/daoudat/py/pyGeno/mouse', 'mouse', 'reference2')
	#print 'install b6'
	#installGenome_casava('mouse', 'B6', '/u/corona/Project_DSP014/120313_SN942_0105_AD093KACXX/Build_B6/snps.txt')
	
