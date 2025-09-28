/*
	Original author of the starter code
    Tanzir Ahmed
    Department of Computer Science & Engineering
    Texas A&M University
    Date: 2/8/20
	
	Please include your Name, UIN, and the date below
	Name: Zavier Vega-Yu
	UIN: 
	Date: 
*/
#include "common.h"
#include "FIFORequestChannel.h"

using namespace std;


int main (int argc, char *argv[]) {
	int opt;
	int p = -1;
	double t = -1;
	bool c = false;
	int e = 1;
	string filename = "";
	int buffercapacity = MAX_MESSAGE;

	while ((opt = getopt(argc, argv, "p:t:e:f:m:c")) != -1) {
		switch (opt) {
			case 'p':
				p = atoi (optarg);
				break;
			case 't':
				t = atof (optarg);
				break;
			case 'e':
				e = atoi (optarg);
				break;
			case 'f':
				filename = optarg;
				break;
			case 'c':
				c = true;
				break;
			case 'm':
				buffercapacity = atoi (optarg);
				break;
		}
	}

	/** 4.1 Run the server as a child process */
	if (fork() == 0) {
		string buffer_str = to_string(buffercapacity);
		const char* args[] = {"./server", "-m", buffer_str.c_str(), NULL};
		execvp(args[0], const_cast<char* const*>(args));
		
		cout << "The server child process failed to execute" << endl;
		return 1;
	}

    FIFORequestChannel chan("control", FIFORequestChannel::CLIENT_SIDE);
	FIFORequestChannel *active_chan = &chan;

	/** 3.4 New Channel Creation Request */
	if (c) {
		char* buf = new char[buffercapacity];
		MESSAGE_TYPE mtype = NEWCHANNEL_MSG;
		memcpy(buf, &mtype, sizeof(MESSAGE_TYPE));
		chan.cwrite(buf, sizeof(MESSAGE_TYPE));
		
		char buf2[30];
		chan.cread(buf2, 30);

		string new_channel_name(buf2);

		FIFORequestChannel* new_chan = new FIFORequestChannel(new_channel_name, FIFORequestChannel::CLIENT_SIDE);
		active_chan = new_chan;
		delete[] buf;
	}

	/** 4.2 Requesting Data Points */
	if (p >= 0 && t >= 0) {
		char* buf = new char[buffercapacity];
		datamsg x(p, t, e);

		memcpy(buf, &x, sizeof(datamsg));
		active_chan->cwrite(buf, sizeof(datamsg)); // question
		double reply;
		active_chan->cread(&reply, sizeof(double)); //answer
		cout << "For person " << p << ", at time " << t << ", the value of ecg " << e << " is " << reply << endl;
		delete[] buf;
	} else if (p >= 0) {
		string outfile = "received/x" + to_string(p) + ".csv";
		ofstream ofs(outfile.c_str());
		if (!ofs.is_open()) {
			cout << "Could not open " << outfile << endl;
			return 1;
		}

		// Obtain the first 1000 data points
		for (double i = 0; i < 1000; i++) {
			double time = i * 0.004;
			char* buf_ecg1 = new char[buffercapacity];
			char* buf_ecg2 = new char[buffercapacity];

			// Data point for ecg 1:
			datamsg x1(p, time, 1);

			memcpy(buf_ecg1, &x1, sizeof(datamsg));
			active_chan->cwrite(buf_ecg1, sizeof(datamsg)); 
			double val1;
			active_chan->cread(&val1, sizeof(double)); 

			// Data point for ecg 2:
			datamsg x2(p, time, 2);

			memcpy(buf_ecg2, &x2, sizeof(datamsg));
			active_chan->cwrite(buf_ecg2, sizeof(datamsg)); 
			double val2;
			active_chan->cread(&val2, sizeof(double)); 

			ofs << time << "," << val1 << "," << val2 << endl;
			
			delete[] buf_ecg1;
			delete[] buf_ecg2;
		}

		ofs.close();
	}
	

	/** 4.3 Requesting Files */
	if (filename.length() > 0) {
		// Obtain size of file
		filemsg fm(0, 0);
		int len = sizeof(filemsg) + (filename.size() + 1);
		char* buf2 = new char[len];

		memcpy(buf2, &fm, sizeof(filemsg));
		strcpy(buf2 + sizeof(filemsg), filename.c_str());
		
		active_chan->cwrite(buf2, len);  // I want the file length;

		__int64_t filelen;
		active_chan->cread(&filelen, sizeof(__int64_t));
		
		cout << "File " << filename << " has length: " << filelen << " bytes" << endl;
		delete[] buf2;

		string outputfile = "received/" + filename;

		ofstream ofs2(outputfile.c_str());
		if (!ofs2.is_open()) {
			cout << "Could not open " << outputfile << endl;
			return 1;
		}

		// Obtain contents of file
		for (__int64_t offset = 0; offset < filelen; offset += buffercapacity) {
			int length = buffercapacity;
			if (offset + length > filelen) length = filelen - offset;
			
			// Create filemsg object
			filemsg fm(offset, length);

			// Package in a buffer the filemsg + filename
			int len = sizeof(filemsg) + filename.size() + 1;
			char* buf3 = new char[len];

			memcpy(buf3, &fm, sizeof(filemsg));
			strcpy(buf3+sizeof(filemsg), filename.c_str());

			active_chan->cwrite(buf3, len); // request
			
			char* buf4 = new char[length];
			active_chan->cread(buf4, length); // response

			// Write buffer to new file
			ofs2.write(buf4, length);

			delete[] buf3;
			delete[] buf4;
		}

		ofs2.close();
	}
	
	
	// closing the channel    
    MESSAGE_TYPE m = QUIT_MSG;
	cout << "Closing Channel: " << active_chan->name() << endl;
    active_chan->cwrite(&m, sizeof(MESSAGE_TYPE));

	if (c) { delete active_chan; }
}
