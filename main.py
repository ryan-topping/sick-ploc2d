import socket
import time


from datetime import datetime
from typing import Optional
from xml.etree import ElementTree as ET


RUN_LOCATE = "Run.Locate"
RUN_ERROR  = "Run.Locate.Error"
RUN_OK     = "Run.Locate.Ok"


class Result:
    """Represents a result response from a Sick PLOC2D device.
    """
    def __init__(self, 
                 result_id: int,
                 timestamp: datetime,
                 result_type: str,
                 error_code: Optional[int],
                 error_text: str,
                 job_id: int,
                 match_id: int,
                 matches: int,
                 x: float,
                 y: float,
                 z: float,
                 r1: float,
                 r2: float,
                 r3: float,
                 scale: float,
                 score: int,
                 time: int,
                 exposure: int,
                 identified: int):
        self.result_id = result_id
        self.timestamp = timestamp
        self.result_type = result_type
        self.error_code = error_code
        self.error_text = error_text
        self.job_id = job_id
        self.match_id = match_id
        self.matches = matches
        self.x = x
        self.y = y
        self.z = z
        self.r1 = r1
        self.r2 = r2
        self.r3 = r3
        self.scale = scale
        self.score = score
        self.time = time
        self.exposure = exposure
        self.identified = identified


class PLOC2D:
    ERROR_CODES = {
        "9100": "The image acquisition failed.",
        "9101": "The image could not be stored to the SD-card.",
        "9200": "No valid image found.",
        "9210": "PLOC2D not callibrated.",
        "9202": "PLOC2D not aligned.",
        "9203": "Job not valid.",
        "9400": "Alignment failed.",
        "9401": "Alignment target not found.",
        "9600": "Locate failed.",
        "9601": "Locate failed. Score too low.",
        "9999": "An unknown error occured.",
    }

    
class PLOC2DSession:
    """Represents a socket session over TCP/IP with a Sick PLOC2D for automated
    object location implementation.

    Usage:
      Instantiate a new PLOC2D session:
      session = PLOC2DSession("10.78.1.156")
    
      Then connect to the device:
      session.connect()

      and then run jobs:
      result = session.run_job(job_id=1)
      or with a match_id if multiple matches:
      result = session.run_job(job_id=1, match_id=2)

      Alternatively:
      with PLOC2DSession("10.78.1.156").connect() as session:
          result = session.run_job(1)
          etc...

      Access the results from run_job with dot notation:
      result.x      x location compared to origin
      result.y      y location compared to origin
      result.r3     rotation in degrees compared to origin

      Additional information is available in the result:
        timestamp, result_type (ok or error), error_code, error_text,
        job_id, match_id, matches, x, y, z, r1, r2, r3, scale, score,
        time, exposure, identified
      
    Methods:
      connect()     connect to the PLOC2D
      disconnect()  disconnect from the PLOC2D
        
    Functions:
      run_job(job_id)
      run_job(job_id, match_id)
        returns a Result object
    """
    def __init__(self, 
                 ip_address: str, 
                 port: int = 14158,
                 timeout: float = 3.0,
                 encoding: str = "ascii", 
                 buffer: int = 1024) -> None:
        self._ip_address = ip_address
        self._port = port
        self._address = self._ip_address, self._port
        self._timeout = timeout
        self._encoding = encoding
        self._buffer = buffer
        self._connection = None
    
    def connect(self):
        if self._connection is not None:
            return
        self._connection = socket.socket()
        self._connection.settimeout(self._timeout)
        self._connection.connect(self._address)
        return self

    def disconnect(self):
        if self._connection is None:
            return
        self._connection.close()
        self._connection = None

    def run_job(self, job_id: int, match_id: Optional[int] = None) -> Result:

        # Build XML Object
        message_element = ET.Element("message")
        name_element = ET.SubElement(message_element, "name")
        name_element.text = RUN_LOCATE
        job_element = ET.SubElement(message_element, "job")
        job_element.text = str(job_id)
        if match_id is not None:
            match_element = ET.SubElement(message_element, "match")
            match_element.text = str(match_id)

        # Convert to bytes
        command = ET.tostring(message_element)

        # Send command as bytes to PLOC2D
        self._send(command)

        # Receive Response as bytes
        response = self._recv()

        # Check if we received a response
        if response is None:
            return None

        # Convert XML response into dictionary
        parent = ET.fromstring(response)
        data = {child.tag: child.text for child in parent}

        # Result Package
        result_id = int(time.time())
        timestamp = datetime.fromtimestamp(result_id)
        result_type = data.get("name", None)
        error_code = data.get("error", None)
        error_text = PLOC2D.ERROR_CODES.get(error_code, "")
        job_id = job_id
        match_id = int(data.get("match", 0))
        matches = int(data.get("matches", 0))
        x = float(data.get("x", 0))
        y = float(data.get("y", 0))
        z = float(data.get("z", 0))
        r1 = float(data.get("r1", 0))
        r2 = float(data.get("r2", 0))
        r3 = float(data.get("r3", 0))
        scale = float(data.get("scale", 0))
        score = float(data.get("score", 0.0))
        locate_time = int(data.get("time", 0))
        exposure = int(data.get("exposure", 0))
        identified = int(data.get("identified", 0))

        return Result(result_id=result_id, 
                      timestamp=timestamp,
                      result_type=result_type,
                      error_code=error_code,
                      error_text=error_text,
                      job_id=job_id,
                      match_id=match_id,
                      matches=matches,
                      x=x,
                      y=y,
                      z=z,
                      r1=r1,
                      r2=r2,
                      r3=r3,
                      scale=scale,
                      score=score,
                      time=locate_time,
                      exposure=exposure,
                      identified=identified)

    def _send(self, command: bytes):
        if self._connection is None:
            return
        self._connection.send(command)

    def _recv(self) -> bytes:
        if self._connection is None:
            return
        return self._connection.recv(self._buffer)

    def __enter__(self):
        return self
    
    def __exit__(self, *_):
        self.disconnect()
