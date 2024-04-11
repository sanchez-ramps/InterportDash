import base64
import os
import mimetypes
import io

def get_file_attachment(sftp, filename):
    attachment = {}
    with sftp.open(filename, 'r') as file:
        file_content = file.read()
        attachment = get_file_attachment_from_bytes(file_content, filename)
        # print(attachment)
    return attachment

def get_file_attachment_from_bytes(file_content, filename):
    file_data = base64.b64encode(file_content).decode('utf-8')
    # Extract the file name and type
    file_name = os.path.basename(filename)
    file_type, _ = mimetypes.guess_type(file_name)

    attachment = {
        'name': file_name,
        'datas': file_data,
        'mimetype': file_type,  # Optional: Specify the file type
    }
    # print(attachment)
    return attachment

def attachment_from_workbook(workbook, filename):
    output = io.BytesIO()
    workbook.save(output)
    return get_file_attachment_from_bytes(output.getvalue(), filename)
