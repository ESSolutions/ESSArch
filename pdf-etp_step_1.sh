# Note that .sh scripts work only on Mac. If you're on Windows, install Git Bash and use that as your client.

echo 'Killing all Jekyll instances'
kill -9 $(ps aux | grep '[j]ekyll' | awk '{print $2}')
clear

echo "Building PDF-friendly HTML site for Mydoc ...";
#bundle exec jekyll serve --detach --config _config.yml,pdfconfigs/config_ec_pdf.yml;
bundle exec jekyll serve --config _config.yml,pdfconfigs/config_etp_pdf.yml;
echo "done";

#echo "Building the PDF ...";
#prince --javascript --input-list=_site/pdfconfigs/prince-list.txt -o pdf/ec.pdf;
#echo "done";
