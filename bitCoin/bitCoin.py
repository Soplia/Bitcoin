from uuid import uuid4
from flask import Flask, jsonify, request
import hashlib
import json
from time import time
from urllib.parse import urlparse
import requests
import math
 
class Blockchain(object):
    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()
        # 创建“创世块”
        self.new_block(previous_hash=1, proof=100)
 
    def register_node(self, address):
        """
        增加一个新的网络节点到set集合
        :param address: <str>网络地址 'http://172.16.0.50:5000'
        :return: None
        """
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)
 
    def valid_chain(self, chain):
        """
         检查给定的链是否是有效的
        :param chain: <list> 区块链
        :return: <bool> 
        """
        last_block = chain[0]
        current_index = 1
        while current_index < len(chain):
            block = chain[current_index]
            print('{}'.format(last_block))
            print('{}'.format(block))
            # 检验当前block的previous_hash值和前面block的hash值是否相等
            if block['previous_hash'] != self.hash(last_block):
                return False
            # 验证前面block的工作量证明和当前block的工作量证明拼接起来的字符串的hash是否以'abc'为开头
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False
            last_block = block
            current_index += 1
        # 验证通过，返回True
        return True
 
    def resolve_conflicts(self):
        """
        共识算法解决冲突
        使用网络中最长的链.
        :return: <bool> True 如果链被取代, 否则为False
        """
        # 所有的邻居节点
        neighbours = self.nodes
        new_chain = None
        # 在所有邻居中查找比自己链更长的
        max_length = len(self.chain)
        # 遍历并且验证邻居链的有效性
        for node in neighbours:
            response = requests.get('http://{}/chain'.format(node))
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                # 检查链是否更长，且有效。更新new_chain,并更新max_length。
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain
        # 如果new_chain是有定义的，则说明在邻居中找到了链更长的，用new_chain替换掉自己的链
        if new_chain:
            self.chain = new_chain
            return True
        return False
 
    def new_block(self, proof, previous_hash=None):
        """
        生成新块
        :param proof: <int> 工作量证明，它是一个工作算法对应的一个值
        :param previous_hash: (Optional) <str> 前一个区块的hash值
        :return: <dict> 返回一个新的块，这个块block是一个字典结构
        """
        block = {
            # 新block对应的index
            'index': len(self.chain) + 1,
            # 时间戳，记录区块创建的时间
            'timestamp': time(),
            # 记录当前的交易记录，即通过new_transactions创建的交易，记录在这个新的block里
            'transactions': self.current_transactions,
            # 工作量证明
            'proof': proof,
            # 前一个block对应的hash值
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }
        # 重置当前的交易，用于记录下一次交易
        self.current_transactions = []
        # 将新生成的block添加到block列表中
        self.chain.append(block)
        # 返回新创建的blcok
        return block
 
    def new_transaction(self, sender, recipient, amount):
        """
        生成新交易信息，信息将加入到下一个待挖的区块中
        :param sender: <str> 发送者的地址
        :param recipient: <str> 接受者的地址
        :param amount: <int> 交易额度
        :return: <int> 返回新的Block的Id值，新产生的交易将会被记录在新的Block中
        """
        # 实现很简单，向交易列表中添加一个字典，这个字典中记录交易双发的信息
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })
        # 返回最后一个区块的index加上1，即对应到新的区块上
        return self.last_block['index'] + 1
 
    @staticmethod
    def hash(block):
        """
        生成块的 SHA-256 hash值
        :param block: <dict> Block
        :return: <str>
        """
        # 首先将block字典结构转换成json字符串，通过sort_keys指定按key拍好序。
        block_string = json.dumps(block, sort_keys=True).encode()
        # 调用sha256函数求取摘要
        return hashlib.sha256(block_string).hexdigest()
 
    @property
    def last_block(self):
        return self.chain[-1]
 
    def proof_of_work(self, last_proof):
        """
        简单的工作量证明:
         - 查找一个数 p 使得 hash(p+last_proof) 以'abc'开头
         - last_proof 是上一个块的证明,  p是当前的证明
        :param last_proof: <int>
        :return: <int>
        """
        proof = 0
        # 定义一个死循环，直到valid_proof验证通过
        while self.valid_proof(last_proof, proof) is False:
            proof += math.pi
        return proof
 
    @staticmethod
    def valid_proof(last_proof, proof):
        """
        验证证明: 是否hash(last_proof, proof)以'abc'开头?
        :param last_proof: <int> 前一个证明
        :param proof: <int> 当前证明
        :return: <bool> 
        """
        guess = '{}{}'.format(last_proof, proof).encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:3] == "abc"
 
#实例化一个Flask节点
app = Flask(__name__)
 
# 为当前节点生成一个全局唯一的地址，使用uuid4方法
node_identifier = str(uuid4()).replace('-', '')
 
#初始化区块链
blockchain = Blockchain()
 
# 告诉服务器去挖掘新的区块
@app.route('/mine', methods=['GET'])
def mine():
    #获取区块链最后一个block
    last_block = blockchain.last_block
    #取出最后一个block的proof工作量证明
    last_proof = last_block['proof']
     # 运行工作量的证明和验证算法，得到proof。
    proof = blockchain.proof_of_work(last_proof)
 
    # 给工作量证明的节点提供奖励.
    # 发送者为 "0" 表明是新挖出的币
    # 接收者是我们自己的节点，即上面生成的node_identifier。实际中这个值可以用用户的账号。
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # 产生一个新的区块，并添加到区块链中
    block = blockchain.new_block(proof)

    #构造返回响应信息
    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200
 
 # 创建一个交易并添加到区块，POST接口可以给接口发送交易数据
@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    #获取请求的参数，得到参数的json格式数据
    values = request.get_json()
    print('request parameters:%s'%(values))
    #检查请求的参数是否合法，包含sender,recipient,amount几个字段
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400
 
    # 使用blockchain的new_transaction方法创建新的交易
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])
    #构建response信息
    response = {'message': 'Transaction will be added to Block {}'.format(index)}
    #返回响应信息
    return jsonify(response), 201
 
@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400
    #注册节点到blockchain中
    for node in nodes:
        blockchain.register_node(node)
     #构造一个响应
    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
  #201：提示知道新文件的URL
    return jsonify(response), 201
 
@app.route('/nodes/resolve', methods=['GET'])
def consensus():
   #调用resolve_conficts()方法，让网络中的chain协调一致
    replaced = blockchain.resolve_conflicts()
    #如果当前节点的chain被替换掉，返回替换掉的信息；否则返回当前节点的chain是有权威的！
    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }
    return jsonify(response), 200
 
#返回整个区块链，GET接口
@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200
 
if __name__ == '__main__':
    from argparse import ArgumentParser
 
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port
    app.run(host='127.0.0.1', port=port)