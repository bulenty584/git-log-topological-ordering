import os
import sys
import zlib


class CommitNode:
    def __init__(self, commit_hash):
        """
        :type commit_hash: str
        """
        self.commit_hash = commit_hash
        self.parents = []
        self.children = []


def find_git_dir(path = os.getcwd()):
    """
    Recursively search for the .git directory
    in the given path and its parent directories.
    """
    
    # get current working directory
    current_dir = path
    if os.path.exists(f'{current_dir}/.git'):
        return current_dir
    elif current_dir == '/':
        # If we reach the root directory means we're not inside a Git repo
        sys.stderr.write('Not inside a Git repository\n')
        sys.exit(1)
    else:
        return find_git_dir(os.path.dirname(current_dir))


def get_branch_names(git_directory):
    branches_path = os.path.join(git_directory, '.git', 'refs', 'heads')
    branches = {}
    for root, dirs, files in os.walk(branches_path):
        for file in files:
            branch_path = os.path.join(root, file)
            branch_name = os.path.relpath(branch_path, branches_path)
            with open(branch_path, 'r') as f:
                commit_hash = f.read().strip()
            branches[branch_name] = commit_hash
    return branches


def map_hash_to_branch():
    git_dir = find_git_dir()
    branch = get_branch_names(git_dir)
    hash_to_branch = {}
    for b, commit in branch.items():
        if commit not in hash_to_branch:
            hash_to_branch[commit] = []
        hash_to_branch[commit].append(b)  # Append branch name to the list
    return hash_to_branch


def build_commit_graph():
    git_dir = find_git_dir()
    branches = get_branch_names(git_dir)
    graph = dict()
    visited = set()  # To keep track of visited commits
    processing_list = set(branches.values())  # Initialize with branch heads

    while processing_list:
        current_commit = processing_list.pop()  # Pick a hash from the list

        if current_commit in visited:  # Skip if visited
            continue  # Mark as visited

        if current_commit not in graph:  # Create a node if not in the graph
            graph[current_commit] = CommitNode(current_commit)

        commit_object = graph[current_commit]

        # Retrieve parent commits using zlib for decompression
        try:
            dir_path = current_commit[:2]
            commit_parent = current_commit[2:]
            rel_path = f"{git_dir}/.git/objects"
            abs_path = os.path.join(rel_path, dir_path, commit_parent)
            obj_file = open(abs_path, 'rb')
            decompressed_data = zlib.decompress(obj_file.read())
            obj_file.close()
        except FileNotFoundError:
            # Handle missing commit objects gracefully
            continue
        parent_hashes = []
        for line in decompressed_data.decode().split("\n"):
            if line.startswith("parent"):
                parent_commit = line[7:].strip()
                parent_hashes.append(parent_commit)
                commit_object.parents.append(parent_commit)
        for parent in parent_hashes:
            if parent not in visited:  # Add unvisited parent to process list
                processing_list.add(parent)

            if parent not in graph:  # Create a parent node if not in the graph
                graph[parent] = CommitNode(parent)

            # Update children/parents relationships
            graph[parent].children.append(current_commit)
        visited.add(current_commit)

    return graph


def topo_sort():
    graph = build_commit_graph()
    sorted_commits = []
    commits_to_process = []
    eligible_commits = graph.keys()

    for commit in eligible_commits:
        if (len(graph[commit].children) == 0):
            commits_to_process.append(commit)

    while commits_to_process:
        commit = commits_to_process.pop()
        sorted_commits.append(commit)
        for parent in graph[commit].parents:
            graph[parent].children.remove(commit)
            if not graph[parent].children:
                commits_to_process.append(parent)
        graph[commit].parents.clear()

    if len(sorted_commits) != len(graph):
        raise Exception("Error: The sorted list does not include all commits.")

    return sorted_commits


def print_graph():
    hash_to_branch = map_hash_to_branch()
    sorted_commits = topo_sort()
    graph = build_commit_graph()
    last_commit = None

    for i, commit in enumerate(sorted_commits):
        node = graph[commit]

        # Print commit hash and associated branch names
        branch_names = " ".join(sorted(hash_to_branch.get(commit, [])))
        print(f"{commit} {branch_names}".strip())

        # Sticky End
        # Check if next commit is not a direct child
        if i + 1 < len(sorted_commits):
            if sorted_commits[i + 1] not in node.parents:
                # If there are parents, print last parent hash followed by "="
                if node.parents:
                    parents_str = " ".join(node.parents)
                    print(f"{parents_str}=")
                else:
                    # No parents, so just print "="
                    print("=")
                print()  # Print empty line
                last_commit = None
            else:
                last_commit = commit

        # Sticky Start
        # Check if this is the start of a new segment
        if last_commit is None and i + 1 < len(sorted_commits):
            last_commit = sorted_commits[i + 1]
            node = graph[last_commit]
            children_str = " ".join(node.children)
            print(f"={children_str}")


def topo_order_commits():

    # Print the topologically sorted graph
    print_graph()


if __name__ == '__main__':
    topo_order_commits()
