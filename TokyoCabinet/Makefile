CXX=g++
CXX_FLAGS=-std=c++14
CXX_LIBS=-ltokyocabinet

tokyo_cabinet_set: tokyo_cabinet_set.cpp
	$(CXX) -ggdb3 $(CXX_FLAGS) $< -o $@ $(CXX_LIBS)

clean:
	rm -rf tokyo_cabinet_set

.PHONY: clean
