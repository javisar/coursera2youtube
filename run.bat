@echo off
python -u %~dp0\coursera\coursera-dl -u javisar@gmail.com -p XXXXXXXXX --about --combined-section-lectures-nums --path=./downloads/ %1
python -u %~dp0\upload-youtube.py --path=./downloads/%1 --name="Test name" --description="Test description"
exit
