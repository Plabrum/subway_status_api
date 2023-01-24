import os
import datetime
import requests
import pytz

all_trains = [ "A", "C","E","B","D","F","M","G","L","J","Z","N","Q","R","W","1","3","2","4","5","6","7","GS","SI"]

def get_alerts(mta_key, json_out=False) -> dict:
	local_tz = pytz.timezone('US/Eastern') # use your local timezone name here

	def utc_to_est(utc_dt: datetime.datetime) -> datetime.datetime:
		local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
		return local_dt

	def nix_to_utc(timestamp: str) -> datetime.datetime:
		int_timestamp = int(timestamp)
		return datetime.datetime.utcfromtimestamp(int_timestamp)

	def nix_to_est(timestamp:str) -> datetime.datetime:
		utc_time = nix_to_utc(timestamp)
		est_time = utc_to_est(utc_time)
		return est_time
		
	def str_format(dt: datetime.datetime) -> str:
		return dt.strftime('%Y-%m-%d %H:%M:%S')

	def time_convert(time: str) -> str:
		'''
		Takes either a nix timestamp or a iso form and converts to human readable form
		'''
		if len(time) < 9:
			return time
		elif len(time) < 11:
			# Must be a nix timestamp
			return str_format(nix_to_est(time))
		else:
			dt = datetime.datetime.fromisoformat(time)
			return str_format(dt)
			
	
	uri = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fsubway-alerts.json"

	r = requests.get(uri, headers={ "x-api-key": mta_key}, timeout=5)
	if not r.status_code == 200:
		return {"body": f"MTA API Error - {r.status_code}"}
	records = r.json()['entity']
	train_dict = {}

	def add_alert(train, alert_type, combined_report, hard_init=False):
		if hard_init:
			for t in train:
				train_dict[train] = {"current":[], "future": [], "past":[], "breaking":[]}
		else:
			if train not in train_dict:
				train_dict[train] = {"current":[], "future": [], "past":[], "breaking":[]}

			train_dict[train][alert_type].append(combined_report)

	add_alert(train=all_trains, alert_type=None, combined_report=None, hard_init=True)
	for record in records:

		now = pytz.timezone('US/Eastern').localize(datetime.datetime.now())
		alert_times = record['alert']["active_period"][0]
		alert_start = nix_to_est(alert_times['start'])
		iso_start = alert_start.isoformat()
		alert_type = None

		if 'end' in alert_times.keys():
			alert_end = nix_to_est(alert_times['end'])
			iso_end = alert_end.isoformat()
		else:
			alert_end = None
			iso_end = ""
		
		if alert_end == None:
			alert_type = "breaking"
		elif alert_end < now:
			alert_type = "past"
		elif now < alert_start:
			alert_type = "future"
		elif (alert_start < now) and (now < alert_end):
			alert_type = "current"
		else:
			print("ERROR")
			continue
		
		train = record['alert']['informed_entity'][0]["route_id"]
		report = record['alert']["header_text"]['translation'][0]['text']
		# print(train)
		combined_report = {"start": iso_start, "end": iso_end, 'report':report}

		add_alert(train=train, alert_type=alert_type, combined_report=combined_report)

	if json_out:
		return train_dict
	else:
		# Converting the train dict to a list of trains (because javascript can't easily iterate key,value pairs? - so dumb)
		train_list = [{"train": train, "all_reports": reports} for train, reports in train_dict.items()]
		return train_list



def main(args=None):
	mta_key = os.environ.get("mta_key")
	return {"body": get_alerts(mta_key=mta_key, json_out=False)}

if __name__ == '__main__':
	from dotenv import load_dotenv
	from ignore import local_helper
	load_dotenv()
	main_output = main()
	local_helper.print_reports(main_output["body"])


	