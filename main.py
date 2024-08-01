import socket
import threading
import sys
import gzip


def parse_request(conn, buffersize=1024):
    parsed_req = {}
    headers = {}
    body = []
    rest = ''
    target = 0
    body_len = 0
    body_count = 0

    while data := conn.recv(buffersize).decode():
        if rest:
            data = rest + data

        if target == 0: # request line
            ind = data.find('\r\n')
            if ind == -1:
                rest = data
                continue
            line = data[:ind].split()
            data = data[ind+2:]
            parsed_req['method'] = line[0]
            parsed_req['url'] = line[1]
            target = 1

        if target == 1: # headers
            if not data:
                continue
            while True:
                ind = data.find('\r\n')
                if ind == -1:
                    rest = data
                    break
                if ind == 0:  # the case for boundary (\r\n\r\n)
                    data = data[ind+2:]
                    target = 2
                    break
                line = data[:ind].split(': ', maxsplit=1)
                data = data[ind+2:]
                headers[line[0].lower()] = line[1] # adding the headers with names as keys in lowercase
            if target == 1:
                continue

        if target == 2: # troubleshooting content-length header
            if 'content-length' not in headers:
                break
            body_len = int(headers['content-length'])
            if not body_len:
                break
            target = 3

        if target == 3: # scaning the body
            body.append(data)
            body_count += len(data)
            if body_count >= body_len:
                break

    parsed_req['body'] = body
    return parsed_req, headers


def c_handler(client, addr):
    request, headers = parse_request(client)
    response = "HTTP/1.1 404 Not Found\r\n\r\n".encode()
    req_command = request['url']
    mode = request['method']
    print(headers)

    if req_command == '/':
        response = "HTTP/1.1 200 OK\r\n\r\n".encode()
    elif req_command.startswith('/echo/'):
        string = req_command.strip('/echo/')
        if 'accept-encoding' in headers:
            if 'gzip' in headers['accept-encoding']:
                string = gzip.compress(string.encode())
                response = f'HTTP/1.1 200 OK\r\nContent-Encoding: gzip\r\nContent-Type: text/plain\r\nContent-Length: {len(string)}\r\n\r\n{string}'.encode()
            else:
                response = f'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(string)}\r\n\r\n{string}'.encode()
        else:
            print(req_command)
            response = f'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(string)}\r\n\r\n{string}'.encode()
    elif req_command == '/user-agent':
        user_agent = headers['user-agent']
        response = f'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(user_agent)}\r\n\r\n{user_agent}'.encode()
    elif req_command.startswith('/files'):
        if mode == 'GET':
            directory = sys.argv[2]
            filename = req_command[7:]
            try:
                with open(f'/{directory}/{filename}') as file:
                    body = file.read()
                response = f'HTTP/1.1 200 OK\r\nContent-Type: application/octet-stream\r\nContent-Length: {len(body)}\r\n\r\n{body}'.encode()
            except Exception:
                pass
        elif mode == 'POST':
            directory = sys.argv[2]
            filename = req_command[7:]
            content = request['body']
            with open(f'/{directory}/{filename}', 'w') as file:
                file.write(''.join(content))
            response = 'HTTP/1.1 201 Created\r\n\r\n'.encode()

    client.send(response)

    client.close()

def main():
    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    client: socket.socket
    server_socket.listen()
    while True:
        client, addr = server_socket.accept()
        threading.Thread(target=c_handler, args=(client, addr)).start()

    server_socket.close()

if __name__ == "__main__":
    main()
