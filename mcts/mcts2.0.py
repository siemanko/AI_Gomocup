import random
import copy
import math as np
import time

MAX_BOARD = 20
board = [[0 for i in range(MAX_BOARD)] for j in range(MAX_BOARD)]


class Node:

    def __init__(self, move, players_in_turn=None, UCB=0, parent=None,
                 num_child=-1, possible_moves_for_child=None, possible_moves_for_expansion=None):
        self.move = move
        self.UCB = UCB  # not used yet
        self.parent = parent
        self.children = []
        self.sim_num = 0
        self.win_num = 0
        self.max_num_child = num_child
        # inherit the possible moves for this node's children, similar to board.availables
        # so not used yet
        self.possible_moves_for_child = copy.deepcopy(possible_moves_for_child)

        self.possible_moves_for_expansion = copy.deepcopy(possible_moves_for_expansion)

        if parent is not None:
            if parent.max_num_child > 0:
                self.max_num_child = parent.max_num_child - 1
            # avoid expanding a move twice
            parent.possible_moves_for_expansion.remove(move)
            # independently inherit
            self.possible_moves_for_child = copy.deepcopy(parent.possible_moves_for_child)
            self.possible_moves_for_child.remove(move)
            self.possible_moves_for_expansion = copy.deepcopy(self.possible_moves_for_child)

            self.opponent = parent.player
            self.player = parent.opponent
        else:
            "zs: note that here is reverse because root is used to be your opponent's turn!!!"
            self.player = players_in_turn[1]
            self.opponent = players_in_turn[0]
        if parent is not None:
            parent.children.append(self)


class Board:

    def __init__(self, input_board, n_in_line=5):
        assert type(n_in_line) == int, "n_in_line para should be INT!"
        self.width = len(input_board[0])
        self.height = len(input_board)
        self.board = copy.deepcopy(input_board)
        self.n_in_line = n_in_line
        self.availables = set([
            (i, j) for i in range(self.height) for j in range(self.width) if input_board[i][j] == 0
        ])
        self.winner = None

    def is_free(self, x, y):
        return 1 if self.board[x][y] == 0 else 0

    def update(self, player, move, check_win=True):
        """
        update the board and check if player wins, so one should use like this:
            if board.update(player, move):
                winner = board.winner
        :param player: the one to take the move
        :param move: a tuple (x, y)
        :param check_win: built for periods when you are sure no one wins
        :return: 1 denotes player wins and 0 denotes not
        """
        assert len(move) == 2, "move is invalid, len = {}".format(len(move))
        self.board[move[0]][move[1]] = player
        self.availables.remove(move)

        if check_win:
            """check if player win"""
            x_this, y_this = move
            # get the boundaries
            up = min(x_this, self.n_in_line - 1)
            down = min(self.height - 1 - x_this, self.n_in_line - 1)
            left = min(y_this, self.n_in_line - 1)
            right = min(self.width - 1 - y_this, self.n_in_line - 1)
            # \
            up_left = min(up, left)
            down_right = min(down, right)
            for i in range(up_left + down_right - self.n_in_line + 2):
                a = [
                    self.board[x_this - up_left + i + j][y_this - up_left + i + j] for j in range(self.n_in_line)
                ]
                assert len(a) == self.n_in_line, "error when check if win on board"
                if len(set(a)) == 1 and a[0] > 0:
                    self.winner = player
                    return 1
            # /
            up_right = min(up, right)
            down_left = min(down, left)
            for i in range(up_right + down_left - self.n_in_line + 2):
                a = [
                    self.board[x_this - up_right + i + j][y_this + up_right - i - j] for j in range(self.n_in_line)
                ]
                assert len(a) == self.n_in_line, "error when check if win on board"
                if len(set(a)) == 1 and a[0] > 0:
                    self.winner = player
                    return 1
            # --
            for i in range(left + right - self.n_in_line + 2):
                a = [
                    self.board[x_this][y_this - left + i + j] for j in range(self.n_in_line)
                ]
                assert len(a) == self.n_in_line, "error when check if win on board"
                if len(set(a)) == 1 and a[0] > 0:
                    self.winner = player
                    return 1
            # |
            for i in range(up + down - self.n_in_line + 2):
                a = [
                    self.board[x_this - up + i + j][y_this] for j in range(self.n_in_line)
                ]
                assert len(a) == self.n_in_line, "error when check if win on board"
                if len(set(a)) == 1 and a[0] > 0:
                    self.winner = player
                    return 1
        # no one wins
        return 0


class MCTS:

    def __init__(self, input_board, players_in_turn, n_in_line=5,
                 confidence=2, time_limit=5.0, max_simulation=5, max_simulation_one_play=50):
        self.time_limit = float(time_limit)
        self.max_simulation = max_simulation
        self.max_simulation_one_play = max_simulation_one_play
        self.MCTSboard = Board(input_board, n_in_line)     # a deep copy Board class object
        self.confidence = confidence                       # confidence level of exploration
        self.player_turn = players_in_turn
        self.player = self.player_turn[0]                  # always the AI first when calling this Algorithm
        self.max_depth = 1
        self.root = Node(None,
                         players_in_turn=players_in_turn,  # here is a reverse, because root is your opponent
                         num_child=len(self.MCTSboard.availables),
                         possible_moves_for_child=self.MCTSboard.availables,
                         possible_moves_for_expansion=self.MCTSboard.availables)

    def get_player(self, player):
        """play one by one"""
        p = {
            self.player_turn[0]: self.player_turn[1],
            self.player_turn[1]: self.player_turn[0],
        }
        return p[player]

    def get_action(self):
        if len(self.MCTSboard.availables) == 1:
            return self.MCTSboard.availables[0]  # the only choice

        num_nodes = 0
        begin_time = time.time()
        while time.time() - begin_time < self.time_limit:
            # run MCTS
            # Selection & Expansion
            node_to_expand = self.select_and_expand()

            # Simulation & back propagation
            for _ in range(self.max_simulation):
                board_deep_copy = copy.deepcopy(self.MCTSboard)
                self.simulate_and_bp(board_deep_copy, node_to_expand)

            num_nodes += 1
        print("total nodes expanded in one action:{}".format(num_nodes))
        print('Maximum depth searched in one action:', self.max_depth)

        percent_wins, move = max(
            (child.win_num / child.sim_num, child.move)
            for child in self.root.children
        )  # choose a move with highest winning rate
        # for child in self.root.children:
        #     print(child.win_num / child.sim_num, child.sim_num, child.move)
        # print('=-' * 20)
        # print(percent_wins, move)
        # print(len(self.root.children))

        return move

    def select_and_expand(self):
        "Selection: greedy search based on UCB value"
        cur_node = self.root
        while cur_node.children:
            # check if current node is fully expanded
            if len(cur_node.children) < cur_node.max_num_child:
                break
            # print('ddd')
            ucb, select_node = 0, None
            for child in cur_node.children:

                ucb_child = child.win_num / child.sim_num + np.sqrt(
                    2 * np.log(cur_node.sim_num) / child.sim_num
                )
                if ucb_child >= ucb:
                    ucb, select_node = ucb_child, child
            cur_node = select_node

        "Expansion: randomly expand a node"
        expand_move = random.choice(list(cur_node.possible_moves_for_expansion))
        expand_node = Node(expand_move, parent=cur_node)
        return expand_node

    def simulate_and_bp(self, cur_board, expand_node):
        # first get to the board now
        _node = expand_node

        while _node.parent.move:
            _node = _node.parent
            cur_board.update(_node.player, _node.move, check_win=False)

        "Simulation: do simulation randomly"
        availables = cur_board.availables
        if len(availables) == 0:
            return

        player = expand_node.player
        win = cur_board.update(player, expand_node.move)

        for t in range(1, self.max_simulation_one_play + 1):
            is_full = not len(availables)
            if win or is_full:
                break

            player = self.get_player(player)
            move = random.choice(list(availables))
            win = cur_board.update(player, move)

        "Back propagation"
        cur_node = expand_node
        while cur_node:
            cur_node.sim_num += 1
            if win and cur_node.player == player:
                # print('--------', player)
                # for row in cur_board.board:
                #     print(' '.join([str(i) for i in row]))
                cur_node.win_num += 1
            cur_node = cur_node.parent
        # print(expand_node.move, expand_node.sim_num, expand_node.win_num)
        # print(expand_node.parent.move, expand_node.parent.sim_num, expand_node.parent.win_num)


class PP:
    # zs: to simulate the pisqpipe package
    def __init__(self):
        self.height = MAX_BOARD
        self.width = MAX_BOARD
        self.terminateAI = None

    def pipeOut(self, what):
        print(what)

    def do_mymove(self, x, y):
        brain_my(x, y)
        self.pipeOut("{},{}".format(x, y))

    def do_oppmove(self, x, y):
        brain_opponents(x, y)
        self.pipeOut("{},{}".format(x, y))


def brain_turn():
    """
    MCTS
    Useful materials:
        class:
            Board
            MCTS
    """
    if pp.terminateAI:
        return

    MCTS_AI = MCTS(board,
                   players_in_turn=[1, 2],  # brain is 1
                   n_in_line=5,
                   confidence=2,
                   time_limit=10,
                   max_simulation=20,
                   max_simulation_one_play=200)

    i = 0
    while True:
        move = MCTS_AI.get_action()
        x, y = move
        if MCTS_AI.MCTSboard.winner:
            print("Winner: {}".format(MCTS_AI.MCTSboard.winner))
            break

        if pp.terminateAI:
            return

        if isFree(x, y):
            break
    if i > 1:
        # zs: maybe useful to debug
        pp.pipeOut("DEBUG {} coordinates didn't hit an empty field".format(i))
    pp.do_mymove(x, y)


def brain_init():
    if pp.width < 5 or pp.height < 5:
        pp.pipeOut("ERROR size of the board")
        return
    if pp.width > MAX_BOARD or pp.height > MAX_BOARD:
        pp.pipeOut("ERROR Maximal board size is {}".format(MAX_BOARD))
        return

    pp.pipeOut("OK")


def brain_restart():
    for x in range(pp.width):
        for y in range(pp.height):
            board[x][y] = 0

    pp.pipeOut("OK")


def isFree(x, y):
    """whether (x, y) is available"""
    return 0 <= x < pp.width and 0 <= y < pp.height and board[x][y] == 0


def brain_my(x, y):
    """my turn: take the step on (x,y)"""
    if isFree(x, y):
        board[x][y] = 1
    else:
        pp.pipeOut("ERROR my move [{},{}]".format(x, y))


def brain_opponents(x, y):
    """oppoent's turn: take the step on (x,y)"""
    if isFree(x, y):
        board[x][y] = 2
    else:
        pp.pipeOut("ERROR opponents's move [{},{}]".format(x, y))


def brain_block(x, y):
    """???"""
    if isFree(x, y):
        board[x][y] = 3
    else:
        pp.pipeOut("ERROR winning move [{},{}]".format(x, y))


def brain_takeback(x, y):
    """take back the chess on (x,y)"""
    if 0 <= x < pp.width and 0 <= y < pp.height and board[x][y] != 0:
        board[x][y] = 0
        return 0
    return 2


def brain_end(x, y):
    pass


def brain_about():
    pp.pipeOut(pp.infotext)


def brain_show():
    st = '  '
    for i in range(len(board[0])):
        if i > 9:
            st += str(i) + ' '
        else:
            st += ' ' + str(i) + ' '
    print(st)
    c = 0
    for row in board:
        if c > 9:
            print(c, end=' ')
        else:
            print('', c, end=' ')
        c += 1
        st = ''
        for ii in row:
            if ii == 1:
                st += 'O  '
            elif ii == 2:
                st += 'X  '
            else:
                st += '-  '
        print(st)


def brain_play():
    while 1:
        print('(if you want to quit, ENTER quit)')
        x = input("Your turn, please give a coordinate 'x y':")
        print()
        if x == 'quit':
            print('You quit.')
            return None
        x = x.split()
        try:
            brain_opponents(int(x[0]), int(x[1]))
        except ValueError or IndexError:
            print('Invalid input!')
            continue
        break
    # brain_show()
    return 0


def main():
    brain_init()
    brain_turn()
    brain_show()

    while brain_play() is not None:
        brain_turn()
        brain_show()


if __name__ == "__main__":
    pp = PP()
    main()
